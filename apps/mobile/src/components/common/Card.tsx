import React from 'react';
import { View, ViewProps } from 'react-native';
import { Colors } from '../../theme/colors';

interface CardProps extends ViewProps {
  children: React.ReactNode;
  padding?: number;
}

export default function Card({ children, padding = 16, style, ...props }: CardProps) {
  return (
    <View
      style={[{
        backgroundColor: Colors.bgCard,
        borderRadius: 20,
        padding,
        borderWidth: 1,
        borderColor: Colors.border,
      }, style]}
      {...props}
    >
      {children}
    </View>
  );
}
