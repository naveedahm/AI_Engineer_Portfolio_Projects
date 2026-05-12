import React from 'react';

interface ConfidenceIndicatorProps {
  confidence: number;
  showText?: boolean;
  size?: 'small' | 'medium' | 'large';
}

export const ConfidenceIndicator: React.FC<ConfidenceIndicatorProps> = ({ 
  confidence, 
  showText = true,
  size = 'small' 
}) => {
  const getColor = () => {
    if (confidence >= 0.8) return 'bg-green-500';
    if (confidence >= 0.6) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  const getText = () => {
    if (confidence >= 0.8) return 'High confidence';
    if (confidence >= 0.6) return 'Medium confidence';
    return 'Low confidence';
  };

  const sizes = {
    small: { dot: 'w-2 h-2', text: 'text-xs' },
    medium: { dot: 'w-3 h-3', text: 'text-sm' },
    large: { dot: 'w-4 h-4', text: 'text-base' }
  };

  return (
    <div className="flex items-center gap-2">
      <div className={`${sizes[size].dot} ${getColor()} rounded-full animate-pulse`} />
      {showText && (
        <span className={`${sizes[size].text} text-gray-600`}>
          {getText()} ({Math.round(confidence * 100)}%)
        </span>
      )}
    </div>
  );
};