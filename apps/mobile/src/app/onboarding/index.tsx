/**
 * Onboarding Step 1 — Welcome & Feature Tour
 * Shown only on first app launch.
 */
import React, { useState, useRef } from 'react';
import {
  View, Text, TouchableOpacity,
  Dimensions, FlatList, ViewToken,
} from 'react-native';
import { useRouter } from 'expo-router';
import { LinearGradient } from 'expo-linear-gradient';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Colors } from '../../theme/colors';

const { width: SCREEN_W } = Dimensions.get('window');

const SLIDES = [
  {
    icon: '🏥',
    title: 'Welcome to MediScan AI',
    subtitle: 'Your personal AI health assistant',
    description:
      'Build a photo health journal with guided capture and fundus upload workflows. Clinical models are still in development.',
    color: Colors.primary,
    bg: ['#FFFFFF', '#F6F7F9'] as [string, string],
  },
  {
    icon: '📷',
    title: '6 Health Scan Modules',
    subtitle: 'Guided camera capture',
    description:
      'Anemia · Skin Disease · Posture & Scoliosis · Eye Disease · Wound Measurement · Tongue Diagnosis\n\nCapture and save photos. Clinical detection is not yet available.',
    color: '#8B5CF6',
    bg: ['#FFFFFF', '#F6F7F9'] as [string, string],
  },
  {
    icon: '💊',
    title: 'Smart Medication Scanner',
    subtitle: 'Barcode · Manual entry · Photo records',
    description:
      'Scan medicine barcodes, photograph prescriptions, or type drug names. Look up US label information from OpenFDA. Pakistan registration and prescription suitability require separate verification.',
    color: '#10B981',
    bg: ['#FFFFFF', '#F6F7F9'] as [string, string],
  },
  {
    icon: '📊',
    title: 'Track & Compare',
    subtitle: 'Monitor your health over time',
    description:
      'Every scan is saved. Compare results over time, get reminders for follow-up scans, and review photos with your clinician.',
    color: '#F59E0B',
    bg: ['#FFFFFF', '#F6F7F9'] as [string, string],
  },
  {
    icon: '🔒',
    title: 'Private & Secure',
    subtitle: 'Local development preview',
    description:
      'This local preview is not HIPAA compliant. Use test data while encryption, privacy controls and comprehensive audit coverage are completed.',
    color: '#3B82F6',
    bg: ['#FFFFFF', '#F6F7F9'] as [string, string],
  },
];

export default function OnboardingScreen() {
  const router = useRouter();
  const [currentIndex, setCurrentIndex] = useState(0);
  const flatListRef = useRef<FlatList>(null);

  const onViewableItemsChanged = useRef(
    ({ viewableItems }: { viewableItems: ViewToken[] }) => {
      if (viewableItems[0]?.index != null) {
        setCurrentIndex(viewableItems[0].index);
      }
    }
  ).current;

  const goNext = () => {
    if (currentIndex < SLIDES.length - 1) {
      flatListRef.current?.scrollToIndex({ index: currentIndex + 1, animated: true });
    } else {
      router.replace('/onboarding/consent');
    }
  };

  const skip = () => {
    router.replace('/onboarding/consent');
  };

  const current = SLIDES[currentIndex];

  return (
    <View style={{ flex: 1, backgroundColor: Colors.bgDark }}>
      <FlatList
        ref={flatListRef}
        data={SLIDES}
        horizontal
        pagingEnabled
        showsHorizontalScrollIndicator={false}
        keyExtractor={(_, i) => String(i)}
        onViewableItemsChanged={onViewableItemsChanged}
        viewabilityConfig={{ viewAreaCoveragePercentThreshold: 50 }}
        renderItem={({ item }) => (
          <View style={{ width: SCREEN_W, flex: 1 }}>
            <LinearGradient
              colors={item.bg}
              style={{ flex: 1, alignItems: 'center', justifyContent: 'center', padding: 32 }}
            >
              {/* Icon */}
              <View style={{
                width: 120, height: 120, borderRadius: 60,
                backgroundColor: `${item.color}20`,
                alignItems: 'center', justifyContent: 'center',
                borderWidth: 2, borderColor: `${item.color}50`,
                marginBottom: 32,
              }}>
                <Text style={{ fontSize: 56 }}>{item.icon}</Text>
              </View>

              <Text style={{
                color: item.color, fontSize: 13, fontWeight: '700',
                textTransform: 'uppercase', letterSpacing: 1.5, marginBottom: 8,
              }}>
                {item.subtitle}
              </Text>

              <Text style={{
                color: Colors.textPrimary, fontSize: 26, fontWeight: '800',
                textAlign: 'center', marginBottom: 16, lineHeight: 34,
              }}>
                {item.title}
              </Text>

              <Text style={{
                color: Colors.textSecondary, fontSize: 15, textAlign: 'center',
                lineHeight: 23, maxWidth: 320,
              }}>
                {item.description}
              </Text>
            </LinearGradient>
          </View>
        )}
      />

      {/* Bottom controls */}
      <SafeAreaView style={{ backgroundColor: Colors.bgDark }} edges={['bottom']}>
        <View style={{ paddingHorizontal: 24, paddingTop: 20, paddingBottom: 16 }}>

          {/* Dots */}
          <View style={{ flexDirection: 'row', justifyContent: 'center', gap: 8, marginBottom: 24 }}>
            {SLIDES.map((_, i) => (
              <TouchableOpacity
                key={i}
                onPress={() => flatListRef.current?.scrollToIndex({ index: i, animated: true })}
              >
                <View style={{
                  height: 8,
                  width: i === currentIndex ? 24 : 8,
                  borderRadius: 4,
                  backgroundColor: i === currentIndex ? current.color : Colors.border,
                }} />
              </TouchableOpacity>
            ))}
          </View>

          {/* Buttons */}
          <View style={{ flexDirection: 'row', gap: 12 }}>
            {currentIndex < SLIDES.length - 1 && (
              <TouchableOpacity
                onPress={skip}
                style={{
                  flex: 0, paddingHorizontal: 20, paddingVertical: 16,
                  borderRadius: 16, borderWidth: 1.5, borderColor: Colors.border,
                }}
              >
                <Text style={{ color: Colors.textSecondary, fontWeight: '600', fontSize: 15 }}>
                  Skip
                </Text>
              </TouchableOpacity>
            )}

            <TouchableOpacity
              onPress={goNext}
              style={{ flex: 1 }}
            >
              <LinearGradient
                colors={[current.color, `${current.color}CC`]}
                start={{ x: 0, y: 0 }}
                end={{ x: 1, y: 0 }}
                style={{
                  borderRadius: 16, paddingVertical: 16,
                  alignItems: 'center',
                }}
              >
                <Text style={{ color: Colors.white, fontWeight: '700', fontSize: 16 }}>
                  {currentIndex < SLIDES.length - 1 ? 'Next →' : 'Get Started'}
                </Text>
              </LinearGradient>
            </TouchableOpacity>
          </View>
        </View>
      </SafeAreaView>
    </View>
  );
}
