import { useCallback, useEffect, useRef, useState } from 'react';
import { ActivityIndicator, Alert, AppState, Linking, Platform, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { CameraView, CameraType, useCameraPermissions } from 'expo-camera';
import { useIsFocused } from '@react-navigation/native';
import * as ImagePicker from 'expo-image-picker';
import * as ImageManipulator from 'expo-image-manipulator';
import * as FileSystem from 'expo-file-system/legacy';
import { pickScanPhoto } from '../../utils/pickScanPhoto';
import { errorMessage } from '../../utils/errorMessage';
import { stableCapture } from '../../utils/captureStability';
import { CaptureGuide, getCaptureGuide } from '../../services/captureService';
import type { ScanModuleInfo } from '../../types';
import { Colors } from '../../theme/colors';

interface Props { module: ScanModuleInfo; onCapture: (uri: string) => void; onAutoCapture?: (uri: string) => void; onClose: () => void }
export default function ScanCamera({ module, onCapture, onAutoCapture, onClose }: Props) {
  const [permission, requestPermission, getPermission] = useCameraPermissions();
  const focused = useIsFocused();
  const [active, setActive] = useState(AppState.currentState === 'active');
  const [facing, setFacing] = useState<CameraType>('back');
  const [ready, setReady] = useState(false);
  const [cameraError, setCameraError] = useState('');
  const [busy, setBusy] = useState(false);
  const [systemOpen, setSystemOpen] = useState(false);
  const [live, setLive] = useState(false);
  const [guide, setGuide] = useState<CaptureGuide | null>(null);
  const [hint, setHint] = useState('Position the selected area inside the guide');
  const [viewport, setViewport] = useState({ width: 1, height: 1 });
  const [frameSize, setFrameSize] = useState({ width: 1, height: 1 });
  const camera = useRef<CameraView>(null);
  const lock = useRef(false);
  const mounted = useRef(true);
  const insecureWeb = Platform.OS === 'web' && typeof window !== 'undefined' && !window.isSecureContext;
  useEffect(() => {
    mounted.current = true;
    const subscription = AppState.addEventListener('change', state => {
      setActive(state === 'active'); if (state !== 'active') { setLive(false); setReady(false); }
      else void getPermission();
    });
    return () => { mounted.current = false; subscription.remove(); };
  }, [getPermission]);
  useEffect(() => { if (!focused) { setLive(false); setReady(false); } }, [focused]);
  const capture = useCallback(async (automatic = false) => {
    if (!camera.current || lock.current || !ready) return;
    lock.current = true; setBusy(true); setLive(false);
    try {
      const photo = await camera.current.takePictureAsync({ quality: .85, skipProcessing: false });
      if (!photo?.uri) throw new Error('No photo returned. Try the phone camera.');
      if (mounted.current) (automatic ? onAutoCapture ?? onCapture : onCapture)(photo.uri);
    } catch (error) { if (mounted.current) Alert.alert('Camera unavailable', errorMessage(error)); }
    finally { lock.current = false; if (mounted.current) setBusy(false); }
  }, [ready, onAutoCapture, onCapture]);
  // Serialized sampled frames, not a 30 fps native frame processor.
  useEffect(() => {
    if (!live || !ready || !focused || !active) return;
    let stopped = false;
    let timer: ReturnType<typeof setTimeout>;
    const controller = new AbortController();
    let previous: CaptureGuide | null = null;
    let stable = 0;
    let lastFrame = 0;
    const poll = async () => {
      if (stopped || lock.current || !camera.current) return;
      lock.current = true;
      let original: string | undefined, resized: string | undefined;
      let auto = false;
      try {
        const photo = await camera.current.takePictureAsync({ quality: .3, skipProcessing: false });
        original = photo?.uri;
        if (!photo?.uri) throw new Error('Camera returned no preview. Use manual capture.');
        if (stopped) return;
        const small = await ImageManipulator.manipulateAsync(photo.uri, [{ resize: { width: 640 } }], { compress: .65, format: ImageManipulator.SaveFormat.JPEG });
        resized = small.uri;
        const result = await getCaptureGuide(module.id, small.uri, controller.signal);
        if (stopped) return;
        const now = Date.now();
        stable = now - lastFrame < 5000 && stableCapture(previous, result) ? stable + 1 : 0;
        previous = result; lastFrame = now;
        setGuide(result); setFrameSize({ width: photo.width, height: photo.height });
        setHint(result.capture_eligible ? `Hold steady · ${Math.min(stable, 3)}/3` : result.guidance);
        auto = stable >= 3;
      } catch (error) {
        if (!stopped) { stable = 0; previous = null; setGuide(null); setHint(errorMessage(error)); setLive(false); }
      } finally {
        lock.current = false;
        if (Platform.OS !== 'web') for (const uri of new Set([original, resized])) {
          if (uri) await FileSystem.deleteAsync(uri, { idempotent: true }).catch(() => undefined);
        }
      }
      if (stopped) return;
      if (auto) { setHint('Capturing photo…'); await capture(true); return; }
      timer = setTimeout(poll, 1200);
    };
    void poll();
    return () => { stopped = true; controller.abort(); clearTimeout(timer); };
  }, [live, ready, focused, active, module.id, capture]);
  const gallery = async () => {
    if (lock.current) return;
    setLive(false); setBusy(true);
    try { const uri = await pickScanPhoto(); if (uri) onCapture(uri); }
    catch (error) { Alert.alert('Photo unavailable', errorMessage(error)); }
    finally { if (mounted.current) setBusy(false); }
  };
  const systemCamera = async () => {
    if (lock.current) return;
    setLive(false); setSystemOpen(true); setReady(false);
    try {
      await new Promise(resolve => setTimeout(resolve, 150));
      if (Platform.OS !== 'web' && !(await ImagePicker.requestCameraPermissionsAsync()).granted) throw new Error('Allow camera access in phone settings.');
      const result = await ImagePicker.launchCameraAsync({ mediaTypes: ['images'], quality: .85 });
      if (!result.canceled && result.assets[0]?.uri) onCapture(result.assets[0].uri);
    } catch (error) { Alert.alert('Camera unavailable', errorMessage(error)); }
    finally { if (mounted.current) setSystemOpen(false); }
  };
  if (!permission) return <View style={styles.permission}><ActivityIndicator /><Text>Loading camera permission…</Text></View>;
  if (!permission.granted || insecureWeb || cameraError) return <View style={styles.permission}>
    <Text style={styles.title}>Open your camera</Text>
    <Text style={styles.help}>{insecureWeb ? 'Live browser camera needs HTTPS. Open this app in Expo Go for live scanning, or use your phone camera below.' : cameraError || 'Allow camera access to take scan photos.'}</Text>
    {!!cameraError && <TouchableOpacity style={styles.button} onPress={() => { setCameraError(''); setReady(false); }}><Text style={styles.buttonText}>Retry live camera</Text></TouchableOpacity>}
    {!insecureWeb && !cameraError && <TouchableOpacity style={styles.button} onPress={async () => {
      try { if (permission.canAskAgain) await requestPermission(); else await Linking.openSettings(); }
      catch (error) { setCameraError(errorMessage(error)); }
    }}><Text style={styles.buttonText}>{permission.canAskAgain ? 'Allow camera' : 'Open phone settings'}</Text></TouchableOpacity>}
    <TouchableOpacity style={styles.button} onPress={systemCamera}><Text style={styles.buttonText}>Use phone camera</Text></TouchableOpacity>
    <TouchableOpacity style={styles.button} onPress={gallery}><Text style={styles.buttonText}>Upload a saved photo</Text></TouchableOpacity>
    <TouchableOpacity onPress={onClose}><Text style={styles.help}>Go back</Text></TouchableOpacity>
  </View>;
  const scale = Math.max(viewport.width / frameSize.width, viewport.height / frameSize.height);
  const box = live && guide?.box;
  const rectangle = box ? { left: box.x * frameSize.width * scale - (frameSize.width * scale - viewport.width) / 2,
    top: box.y * frameSize.height * scale - (frameSize.height * scale - viewport.height) / 2,
    width: box.width * frameSize.width * scale, height: box.height * frameSize.height * scale } : null;
  return <View style={styles.container} onLayout={e => setViewport(e.nativeEvent.layout)}>
    {focused && active && !systemOpen && <CameraView ref={camera} style={StyleSheet.absoluteFill} facing={facing} autofocus="on" animateShutter={false}
      onCameraReady={() => { setReady(true); setCameraError(''); }} onMountError={event => { setCameraError(event.message); setLive(false); }} />}
    <View style={styles.top}>
      <TouchableOpacity onPress={onClose}><Text style={styles.light}>✕ Close</Text></TouchableOpacity><Text style={styles.light}>{module.title}</Text>
      <TouchableOpacity disabled={live || busy} onPress={() => { setReady(false); setFacing(facing === 'back' ? 'front' : 'back'); }}><Text style={styles.light}>Flip</Text></TouchableOpacity>
    </View>
    <View style={styles.guideLayer} pointerEvents="none">
      {!rectangle && <View style={styles.frame}><Text style={styles.frameLabel}>Framing guide · {module.targetArea}</Text></View>}
      {rectangle && <View style={[styles.detected, rectangle]}><Text style={styles.frameLabel}>Person located · YOLOv8</Text></View>}
    </View>
    <View style={styles.bottom}>
      <Text style={styles.light}>{ready ? hint : 'Starting camera…'}</Text>
      <Text style={styles.note}>{module.id === 'Posture' ? 'Person framing only; not scoliosis or disease detection.' : 'Guide and photo-quality checks; body-part recognition is not available.'}</Text>
      <TouchableOpacity disabled={!ready || busy || facing !== 'back'} style={styles.button} onPress={() => { setGuide(null); setHint('Checking framing…'); setLive(!live); }}><Text style={styles.buttonText}>{live ? 'Stop live auto-capture' : 'Start live auto-capture'}</Text></TouchableOpacity>
      {facing === 'front' && <Text style={styles.note}>Switch to the back camera for live auto-capture.</Text>}
      <View style={styles.controls}>
        <TouchableOpacity disabled={busy || live} onPress={gallery}><Text style={styles.light}>Gallery</Text></TouchableOpacity>
        <TouchableOpacity accessibilityLabel="Take photo" disabled={busy || !ready || live} onPress={() => void capture()} style={styles.shutter}>{busy && <ActivityIndicator />}</TouchableOpacity>
        <TouchableOpacity disabled={busy || live} onPress={systemCamera}><Text style={styles.light}>Phone camera</Text></TouchableOpacity>
      </View>
    </View>
  </View>;
}
const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#111' },
  permission: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 24, gap: 18, backgroundColor: Colors.bgDark },
  title: { fontSize: 24, fontWeight: '700', color: Colors.textPrimary }, help: { color: Colors.textSecondary, textAlign: 'center', lineHeight: 24 },
  button: { padding: 14, backgroundColor: Colors.primary, borderRadius: 12, alignItems: 'center', marginVertical: 8 }, buttonText: { color: '#fff', fontWeight: '700' },
  light: { color: '#fff', textAlign: 'center', fontWeight: '600' },
  top: { position: 'absolute', top: 48, left: 16, right: 16, flexDirection: 'row', justifyContent: 'space-between', padding: 12, backgroundColor: '#0009', borderRadius: 12 },
  guideLayer: { ...StyleSheet.absoluteFillObject, justifyContent: 'center', alignItems: 'center', overflow: 'hidden' },
  frame: { width: '70%', aspectRatio: 1, borderWidth: 2, borderColor: '#fff9', borderRadius: 16 },
  detected: { position: 'absolute', borderWidth: 3, borderColor: '#3fe0a0', borderRadius: 8 }, frameLabel: { color: '#fff', backgroundColor: '#0009', fontSize: 11, padding: 6 },
  bottom: { position: 'absolute', bottom: 0, left: 0, right: 0, padding: 18, paddingBottom: 36, backgroundColor: '#000b' },
  note: { color: '#e5e7eb', textAlign: 'center', fontSize: 12, lineHeight: 18, marginTop: 8 }, controls: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 10 },
  shutter: { width: 64, height: 64, backgroundColor: '#fff', borderRadius: 32, borderWidth: 4, borderColor: '#bbb', justifyContent: 'center' },
});
