import React, { useRef, useState, useCallback } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Dimensions,
  Alert,
} from 'react-native';
import { CameraView, CameraType, useCameraPermissions } from 'expo-camera';
import { pickScanPhoto } from '../../utils/pickScanPhoto';
import { LinearGradient } from 'expo-linear-gradient';
import type { ScanModuleInfo } from '../../types';
import { Colors } from '../../theme/colors';

interface ScanCameraProps {
  module: ScanModuleInfo;
  onCapture: (imageUri: string) => void;
  onClose: () => void;
}

const { width: SCREEN_W } = Dimensions.get('window');

export default function ScanCamera({ module, onCapture, onClose }: ScanCameraProps) {
  const [permission, requestPermission] = useCameraPermissions();
  const [facing, setFacing] = useState<CameraType>('back');
  const [capturing, setCapturing] = useState(false);
  const cameraRef = useRef<CameraView>(null);

  const handleCapture = useCallback(async () => {
    if (!cameraRef.current || capturing) return;
    setCapturing(true);
    try {
      const photo = await cameraRef.current.takePictureAsync({
        quality: 0.85,
        base64: false,
        skipProcessing: false,
      });
      if (photo?.uri) {
        onCapture(photo.uri);
      }
    } catch {
      Alert.alert('Error', 'Failed to capture photo. Please try again.');
    } finally {
      setCapturing(false);
    }
  }, [capturing, onCapture]);

  const handleGallery = async () => {
    if (capturing) return;
    setCapturing(true);
    try {
      const uri = await pickScanPhoto();
      if (uri) onCapture(uri);
    } catch (error: unknown) {
      Alert.alert('Photo unavailable', error instanceof Error ? error.message : 'Please choose another photo.');
    } finally {
      setCapturing(false);
    }
  };

  // Request permission
  if (!permission) {
    return <View style={styles.container} />;
  }

  if (!permission.granted) {
    return (
      <View style={[styles.container, { justifyContent: 'center', alignItems: 'center', padding: 24 }]}>
        <Text style={{ color: Colors.textPrimary, fontSize: 18, fontWeight: '700', textAlign: 'center', marginBottom: 12 }}>
          Camera Permission Required
        </Text>
        <Text style={{ color: Colors.textSecondary, textAlign: 'center', marginBottom: 24 }}>
          MediScan AI needs camera access to perform health scans.
        </Text>
        <TouchableOpacity
          onPress={requestPermission}
          style={{ backgroundColor: Colors.primary, paddingHorizontal: 32, paddingVertical: 14, borderRadius: 14 }}
        >
          <Text style={{ color: Colors.white, fontWeight: '700' }}>Grant Permission</Text>
        </TouchableOpacity>
        <TouchableOpacity onPress={handleGallery} disabled={capturing} style={{ padding: 18 }} accessibilityRole="button">
          <Text style={{ color: Colors.primary, fontWeight: '700' }}>Upload a saved photo</Text>
        </TouchableOpacity>
        <TouchableOpacity onPress={onClose} style={{ padding: 12 }} accessibilityRole="button">
          <Text style={{ color: Colors.textSecondary }}>Go back</Text>
        </TouchableOpacity>
      </View>
    );
  }


  return (
    <View style={styles.container}>
      <CameraView ref={cameraRef} style={styles.camera} facing={facing}>
        {/* Top bar */}
        <LinearGradient
          colors={['rgba(0,0,0,0.7)', 'transparent']}
          style={styles.topBar}
        >
          <TouchableOpacity onPress={onClose} style={styles.closeBtn}>
            <Text style={{ color: Colors.white, fontSize: 16 }}>✕</Text>
          </TouchableOpacity>
          <View style={{ flex: 1, alignItems: 'center' }}>
            <Text style={{ color: Colors.white, fontWeight: '700', fontSize: 16 }}>
              {module.icon} {module.title}
            </Text>
          </View>
          <TouchableOpacity
            onPress={() => setFacing(facing === 'back' ? 'front' : 'back')}
            style={styles.flipBtn}
          >
            <Text style={{ color: Colors.white, fontSize: 14 }}>⟳</Text>
          </TouchableOpacity>
        </LinearGradient>

        {/* ROI overlay guide */}
        <View style={styles.overlay}>
          <View style={styles.roiBox}>
            {/* Corner decorators */}
            {[
              { top: -2, left: -2 },
              { top: -2, right: -2 },
              { bottom: -2, left: -2 },
              { bottom: -2, right: -2 },
            ].map((pos, i) => (
              <View
                key={i}
                style={[styles.corner, pos]}
              />
            ))}
          </View>
          <Text style={styles.roiLabel}>{module.targetArea}</Text>
        </View>

        {/* Bottom controls */}
        <LinearGradient
          colors={['transparent', 'rgba(0,0,0,0.85)']}
          style={styles.bottomBar}
        >
          <Text style={styles.instructions} numberOfLines={2}>
            {module.instructions}
          </Text>

          <View style={styles.controls}>
            {/* Gallery picker */}
            <TouchableOpacity onPress={handleGallery} disabled={capturing} style={styles.sideBtn} accessibilityRole="button" accessibilityLabel="Upload a saved photo">
              <Text style={{ color: Colors.white, fontSize: 12, textAlign: 'center' }}>
                🖼️{'\n'}Gallery
              </Text>
            </TouchableOpacity>

            {/* Capture button */}
            <TouchableOpacity
              onPress={handleCapture}
              disabled={capturing}
              style={[styles.captureBtn, { opacity: capturing ? 0.7 : 1 }]}
            >
              <View style={styles.captureBtnInner} />
            </TouchableOpacity>

            {/* Placeholder for symmetry */}
            <View style={styles.sideBtn} />
          </View>
        </LinearGradient>
      </CameraView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.bgDark },
  camera:    { flex: 1 },
  topBar: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingTop: 52,
    paddingBottom: 16,
    paddingHorizontal: 16,
  },
  closeBtn: {
    width: 36, height: 36,
    borderRadius: 18,
    backgroundColor: 'rgba(255,255,255,0.2)',
    alignItems: 'center', justifyContent: 'center',
  },
  flipBtn: {
    width: 36, height: 36,
    borderRadius: 18,
    backgroundColor: 'rgba(255,255,255,0.2)',
    alignItems: 'center', justifyContent: 'center',
  },
  overlay: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  roiBox: {
    width: SCREEN_W * 0.7,
    height: SCREEN_W * 0.7,
    borderWidth: 2,
    borderColor: 'rgba(255,255,255,0.4)',
    borderRadius: 16,
    position: 'relative',
  },
  corner: {
    position: 'absolute',
    width: 20, height: 20,
    borderColor: Colors.primary,
    borderWidth: 3,
    borderRadius: 3,
  },
  roiLabel: {
    color: 'rgba(255,255,255,0.8)',
    fontSize: 13,
    marginTop: 10,
    backgroundColor: 'rgba(0,0,0,0.4)',
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 8,
  },
  bottomBar: {
    paddingBottom: 40,
    paddingTop: 16,
    paddingHorizontal: 24,
  },
  instructions: {
    color: 'rgba(255,255,255,0.8)',
    fontSize: 13,
    textAlign: 'center',
    marginBottom: 20,
    lineHeight: 19,
  },
  controls: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
  },
  sideBtn: { width: 56, alignItems: 'center', justifyContent: 'center' },
  captureBtn: {
    width: 72, height: 72,
    borderRadius: 36,
    backgroundColor: 'rgba(255,255,255,0.3)',
    alignItems: 'center', justifyContent: 'center',
    borderWidth: 3, borderColor: Colors.white,
  },
  captureBtnInner: {
    width: 56, height: 56,
    borderRadius: 28,
    backgroundColor: Colors.white,
  },
});
