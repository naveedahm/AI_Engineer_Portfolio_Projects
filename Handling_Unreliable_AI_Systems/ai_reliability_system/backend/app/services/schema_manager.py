
import json
from typing import Any, Dict, Optional, Union
from jsonschema import validate, ValidationError

class SchemaManager:
    def __init__(self):
        self.schemas = {
            "v1": {
                "type": "object",
                "properties": {
                    "response": {"type": "string"},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "metadata": {"type": "object"}
                },
                "required": ["response"]
            },
            "v2": {
                "type": "object",
                "properties": {
                    "output": {"type": "string"},  # Renamed from 'response'
                    "confidence_score": {"type": "number", "minimum": 0, "maximum": 1},  # Renamed
                    "tokens": {"type": "integer"},  # New field
                    "metadata": {"type": "object"}
                },
                "required": ["output"]
            }
        }
        self.default_version = "v1"
        self.target_version = "v2"  # We want to migrate to v2
    
    def validate(self, response: str, version: str = None) -> str:
        """Validate response against schema with transformation"""
        version = version or self.default_version
        
        if isinstance(response, str):
            # Try to parse as JSON
            try:
                data = json.loads(response)
                
                # Try to validate current version
                try:
                    validate(instance=data, schema=self.schemas[version])
                    return response
                except ValidationError:
                    # Try to transform from other versions
                    transformed = self._try_transform(data)
                    if transformed:
                        return json.dumps(transformed)
                    
                    # If transformation fails, repair
                    return self._repair_response(response)
                    
            except json.JSONDecodeError:
                return self._repair_response(response)
        else:
            return str(response)
    
    def _try_transform(self, data: Dict) -> Optional[Dict]:
        """Try to transform data from various schema versions"""
        
        # Try transforming from v1 to target version
        if self._is_v1_format(data):
            return self.transform_schema(data, self.target_version)
        
        # Try transforming from other versions
        if self._is_legacy_format(data):
            return self._transform_legacy(data)
        
        return None
    
    def _is_v1_format(self, data: Dict) -> bool:
        """Check if data matches v1 schema pattern"""
        return "response" in data or ("text" in data and "score" in data)
    
    def _is_legacy_format(self, data: Dict) -> bool:
        """Check if data matches legacy format"""
        legacy_patterns = [
            "result" in data,
            "answer" in data,
            "completion" in data,
            "message" in data and "content" in data.get("message", {})
        ]
        return any(legacy_patterns)
    
    def _transform_legacy(self, data: Dict) -> Dict:
        """Transform legacy formats to current schema"""
        transformed = {}
        
        # Handle different legacy formats
        if "result" in data:
            transformed["output"] = data["result"]
        elif "answer" in data:
            transformed["output"] = data["answer"]
        elif "completion" in data:
            transformed["output"] = data["completion"]
        elif "message" in data and isinstance(data["message"], dict):
            transformed["output"] = data["message"].get("content", "")
        
        # Add confidence if available
        if "confidence" in data:
            transformed["confidence_score"] = data["confidence"]
        else:
            transformed["confidence_score"] = 0.85
        
        # Add metadata
        transformed["metadata"] = data.get("metadata", {})
        
        return transformed
    
    def transform_schema(self, data: Dict, target_version: str) -> Dict:
        """Transform data between schema versions"""
        transformed = data.copy()
        
        # Handle version-specific transformations
        if target_version == "v2":
            # Transform from v1 to v2
            if "response" in transformed:
                transformed["output"] = transformed.pop("response")
            if "confidence" in transformed:
                transformed["confidence_score"] = transformed.pop("confidence")
            
            # Add default values for new required fields
            if "tokens" not in transformed:
                transformed["tokens"] = 0
            
            # Ensure output exists
            if "output" not in transformed:
                transformed["output"] = str(transformed)
        
        elif target_version == "v1":
            # Transform from v2 to v1
            if "output" in transformed:
                transformed["response"] = transformed.pop("output")
            if "confidence_score" in transformed:
                transformed["confidence"] = transformed.pop("confidence_score")
            if "tokens" in transformed:
                transformed.pop("tokens")  # Remove v2-specific field
        
        return transformed
    
    def _repair_response(self, response: str) -> str:
        """Attempt to repair malformed response"""
        repaired = response.strip()
        
        # Ensure proper JSON structure if needed
        if repaired.startswith('{') and not repaired.endswith('}'):
            repaired += '}'
        
        # Add default structure if completely malformed
        if not repaired or repaired == '{}':
            repaired = '{"output": "No response generated"}'
        elif 'output' not in repaired and 'response' not in repaired and len(repaired) < 200:
            # Wrap in standard format
            escaped = repaired.replace('"', '\\"')
            repaired = f'{{"output": "{escaped}"}}'
        
        return repaired
    
    def get_supported_versions(self) -> list:
        """Get list of supported schema versions"""
        return list(self.schemas.keys())