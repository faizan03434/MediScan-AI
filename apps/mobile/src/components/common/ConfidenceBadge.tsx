import React from 'react';
import { View, Text } from 'react-native';
import { Colors } from '../../theme/colors';

interface ConfidenceBadgeProps {
  score: number; // 0.0 to 1.0
  size?: 'sm' | 'md' | 'lg';
}

export default function ConfidenceBadge({ score, size = 'md' }: ConfidenceBadgeProps) {
  const pct = Math.round(score * 100);

  let color = Colors.success;
  let label = 'High Confidence';

  if (pct < 50) {
    color = Colors.danger;
    label = 'Low Confidence';
  } else if (pct < 70) {
    color = Colors.warning;
    label = 'Moderate';
  }

  const fontSize = size === 'sm' ? 11 : size === 'lg' ? 16 : 13;
  const padding = size === 'sm' ? { paddingHorizontal: 8, paddingVertical: 3 } :
                  size === 'lg' ? { paddingHorizontal: 16, paddingVertical: 8 } :
                  { paddingHorizontal: 12, paddingVertical: 5 };

  return (
    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
      <View style={[{
        backgroundColor: `${color}20`,
        borderRadius: 100,
        borderWidth: 1,
        borderColor: `${color}60`,
        flexDirection: 'row',
        alignItems: 'center',
        gap: 4,
      }, padding]}>
        <View style={{ width: 6, height: 6, borderRadius: 3, backgroundColor: color }} />
        <Text style={{ color, fontSize, fontWeight: '700' }}>
          {score === 0 ? 'Not assessed' : `${pct}% — ${label}`}
        </Text>
      </View>
    </View>
  );
}
