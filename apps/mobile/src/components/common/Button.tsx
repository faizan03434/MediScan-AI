import React from 'react';
import {
  TouchableOpacity,
  Text,
  ActivityIndicator,
  TouchableOpacityProps,
  ViewStyle,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Colors } from '../../theme/colors';

interface ButtonProps extends TouchableOpacityProps {
  title: string;
  variant?: 'primary' | 'secondary' | 'outline' | 'danger' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  loading?: boolean;
  icon?: React.ReactNode;
  fullWidth?: boolean;
}

const sizeStyles = {
  sm: { paddingVertical: 10, fontSize: 13 },
  md: { paddingVertical: 14, fontSize: 16 },
  lg: { paddingVertical: 18, fontSize: 18 },
};

export default function Button({
  title,
  variant = 'primary',
  size = 'md',
  loading = false,
  icon,
  fullWidth = false,
  style,
  disabled,
  ...props
}: ButtonProps) {
  const sizes = sizeStyles[size];
  const isDisabled = disabled || loading;

  if (variant === 'primary') {
    return (
      <TouchableOpacity
        accessibilityRole="button"
        accessibilityLabel={title}
        accessibilityState={{ disabled: !!isDisabled, busy: loading }}
        disabled={isDisabled}
        style={[{ opacity: isDisabled ? 0.6 : 1 }, style as ViewStyle]}
        activeOpacity={0.85}
        {...props}
      >
        <LinearGradient
          colors={[Colors.primary, Colors.primaryDark]}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 0 }}
          style={{ borderRadius: 16, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', paddingHorizontal: 24, paddingVertical: sizes.paddingVertical, width: fullWidth ? '100%' : undefined }}
        >
          {loading ? (
            <ActivityIndicator color={Colors.white} size="small" />
          ) : (
            <>
              {icon}
              <Text style={{ color: Colors.white, fontWeight: '700', fontSize: sizes.fontSize, marginLeft: icon ? 8 : 0 }}>
                {title}
              </Text>
            </>
          )}
        </LinearGradient>
      </TouchableOpacity>
    );
  }

  const variantStyles: Record<string, { bg: string; text: string; border?: string }> = {
    secondary: { bg: Colors.bgCard, text: Colors.textPrimary },
    outline:   { bg: Colors.transparent, text: Colors.primary, border: Colors.primary },
    danger:    { bg: Colors.danger, text: Colors.white },
    ghost:     { bg: Colors.transparent, text: Colors.textSecondary },
  };

  const vs = variantStyles[variant] ?? variantStyles.secondary;

  return (
    <TouchableOpacity
      accessibilityRole="button"
      accessibilityLabel={title}
      accessibilityState={{ disabled: !!isDisabled, busy: loading }}
      disabled={isDisabled}
      activeOpacity={0.8}
      style={[{
        backgroundColor: vs.bg,
        borderWidth: vs.border ? 1.5 : 0,
        borderColor: vs.border,
        borderRadius: 16,
        paddingHorizontal: 24,
        paddingVertical: sizes.paddingVertical,
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'center',
        opacity: isDisabled ? 0.6 : 1,
        width: fullWidth ? '100%' : undefined,
      }, style as ViewStyle]}
      {...props}
    >
      {loading ? (
        <ActivityIndicator color={vs.text} size="small" />
      ) : (
        <>
          {icon}
          <Text style={{ color: vs.text, fontWeight: '700', fontSize: 16, marginLeft: icon ? 8 : 0 }}>
            {title}
          </Text>
        </>
      )}
    </TouchableOpacity>
  );
}
