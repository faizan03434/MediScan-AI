import React, { useState } from 'react';
import {
  View,
  TextInput,
  Text,
  TouchableOpacity,
  TextInputProps,
} from 'react-native';
import { Colors } from '../../theme/colors';

interface InputProps extends TextInputProps {
  label?: string;
  error?: string;
  rightIcon?: React.ReactNode;
  leftIcon?: React.ReactNode;
  isPassword?: boolean;
}

export default function Input({
  label,
  error,
  rightIcon,
  leftIcon,
  isPassword = false,
  style,
  ...props
}: InputProps) {
  const [showPassword, setShowPassword] = useState(false);
  const [focused, setFocused] = useState(false);

  return (
    <View style={{ marginBottom: 16 }}>
      {label && (
        <Text style={{ color: Colors.textSecondary, fontSize: 14, fontWeight: '600', marginBottom: 6 }}>
          {label}
        </Text>
      )}
      <View
        style={{
          flexDirection: 'row',
          alignItems: 'center',
          backgroundColor: Colors.bgInput,
          borderRadius: 14,
          borderWidth: 1.5,
          borderColor: error ? Colors.danger : focused ? Colors.primary : Colors.border,
          paddingHorizontal: 16,
        }}
      >
        {leftIcon && (
          <View style={{ marginRight: 10 }}>{leftIcon}</View>
        )}
        <TextInput
          accessibilityLabel={label}
          style={[{
            flex: 1,
            color: Colors.textPrimary,
            fontSize: 15,
            paddingVertical: 14,
          }, style]}
          placeholderTextColor={Colors.textMuted}
          secureTextEntry={isPassword && !showPassword}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          {...props}
        />
        {isPassword && (
          <TouchableOpacity onPress={() => setShowPassword(!showPassword)}>
            <Text style={{ color: Colors.primary, fontSize: 13 }}>
              {showPassword ? 'Hide' : 'Show'}
            </Text>
          </TouchableOpacity>
        )}
        {rightIcon && !isPassword && (
          <View style={{ marginLeft: 10 }}>{rightIcon}</View>
        )}
      </View>
      {error && (
        <Text style={{ color: Colors.danger, fontSize: 12, marginTop: 4 }}>
          {error}
        </Text>
      )}
    </View>
  );
}
