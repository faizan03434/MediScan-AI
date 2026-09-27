import React from 'react';
import { TouchableOpacity, Text, View } from 'react-native';
import type { ScanModuleInfo } from '../../types';
import { Colors } from '../../theme/colors';

interface Props {
  module: ScanModuleInfo;
  onPress: () => void;
  lastScan?: string; // date string
}

export default function ScanModuleCard({ module, onPress, lastScan }: Props) {
  return (
    <TouchableOpacity
      onPress={onPress}
      activeOpacity={0.8}
      style={{
        backgroundColor: Colors.bgCard,
        borderRadius: 20,
        padding: 16,
        borderWidth: 1,
        borderColor: Colors.border,
        flex: 1,
        minWidth: '47%',
      }}
    >
      {/* Icon circle */}
      <View style={{
        width: 52, height: 52,
        borderRadius: 26,
        backgroundColor: `${module.color}20`,
        alignItems: 'center', justifyContent: 'center',
        marginBottom: 10,
        borderWidth: 1,
        borderColor: `${module.color}40`,
      }}>
        <Text style={{ fontSize: 24 }}>{module.icon}</Text>
      </View>

      <Text style={{ color: Colors.textPrimary, fontWeight: '700', fontSize: 14, marginBottom: 4 }}>
        {module.title}
      </Text>
      <Text style={{ color: Colors.textMuted, fontSize: 12, lineHeight: 16 }} numberOfLines={2}>
        {module.description}
      </Text>

      {lastScan && (
        <View style={{
          marginTop: 10,
          flexDirection: 'row',
          alignItems: 'center',
          gap: 4,
        }}>
          <View style={{ width: 6, height: 6, borderRadius: 3, backgroundColor: Colors.success }} />
          <Text style={{ color: Colors.textMuted, fontSize: 11 }}>
            Last: {lastScan}
          </Text>
        </View>
      )}

      {/* Scan now chip */}
      <View style={{
        marginTop: 10,
        backgroundColor: `${module.color}15`,
        borderRadius: 8,
        paddingHorizontal: 10,
        paddingVertical: 5,
        alignSelf: 'flex-start',
      }}>
        <Text style={{ color: module.color, fontSize: 12, fontWeight: '600' }}>
          Scan Now →
        </Text>
      </View>
    </TouchableOpacity>
  );
}
