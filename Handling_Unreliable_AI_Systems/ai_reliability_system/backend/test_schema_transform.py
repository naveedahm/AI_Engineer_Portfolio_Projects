import json
from app.services.schema_manager import SchemaManager

def test_schema_transformation():
    sm = SchemaManager()
    
    # Test v1 format
    v1_data = {
        "response": "This is a response",
        "confidence": 0.95,
        "metadata": {"source": "test"}
    }
    
    print("Original v1:", json.dumps(v1_data, indent=2))
    transformed = sm.transform_schema(v1_data, "v2")
    print("Transformed to v2:", json.dumps(transformed, indent=2))
    
    # Test legacy format
    legacy_data = {
        "result": "Legacy response",
        "confidence": 0.88
    }
    
    print("\nLegacy format:", json.dumps(legacy_data, indent=2))
    validated = sm.validate(json.dumps(legacy_data))
    print("Validated/transformed:", validated)
    
    # Test OpenAI-style response
    openai_style = {
        "choices": [{
            "message": {
                "content": "OpenAI style response"
            }
        }],
        "usage": {
            "total_tokens": 150
        }
    }
    
    print("\nOpenAI style:", json.dumps(openai_style, indent=2))
    # This would need additional transformation logic
    # validated = sm.validate(json.dumps(openai_style))

if __name__ == "__main__":
    test_schema_transformation()