import React, { useEffect, useMemo, useRef, useState } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as Network from 'expo-network';
import * as ImagePicker from 'expo-image-picker';
import * as DocumentPicker from 'expo-document-picker';
import * as Clipboard from 'expo-clipboard';
import * as Haptics from 'expo-haptics';
import { useAudioRecorder, requestMicrophonePermissionsAsync, RecordingPresets } from 'expo-audio';
import { Ionicons } from '@expo/vector-icons';
import {
  ActivityIndicator,
  Alert,
  Animated,
  FlatList,
  Image,
  KeyboardAvoidingView,
  Linking,
  Modal,
  NativeModules,
  Platform,
  Pressable,
  RefreshControl,
  SafeAreaView,
  ScrollView,
  StatusBar,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import {
  getAndroidAgentStatus,
  openAndroidAccessibilitySettings,
  performAndroidAgentAction,
} from './native/androidAgent';

const COLORS = {
  bg: '#07111f',
  panel: '#0f1b2d',
  panelSoft: '#16263d',
  card: '#132238',
  line: '#243853',
  text: '#edf4ff',
  muted: '#97a8c4',
  cyan: '#6ee7ff',
  blue: '#5ca8ff',
  green: '#7ef0b8',
  amber: '#ffca74',
  coral: '#ff8f83',
};

const TABS = [
  { key: 'chat', label: 'Chat' },
  { key: 'tasks', label: 'Tasks' },
  { key: 'builds', label: 'Builds' },
  { key: 'settings', label: 'Settings' },
];

const STORAGE_KEY = 'ninoclaw-companion-connection';
const DEVICE_ID_KEY = 'ninoclaw-companion-device-id';
const MASCOT = require('./assets/mascot.png');
const BASE_MOBILE_CAPABILITIES = [
  'chat',
  'tasks',
  'builds',
  'settings',
  'mobile_executor',
  'ping',
  'show_alert',
  'open_url',
  'open_settings',
  'dial_number',
  'send_sms',
  'open_maps',
  'open_app',
];

function normalizeBaseUrl(value) {
  return (value || '').trim().replace(/\/+$/, '');
}

function formatTimestamp(value) {
  if (!value) {
    return 'Unknown';
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return String(value);
  }
  return `${date.toLocaleDateString()} ${date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
}

function formatScheduledTime(value) {
  if (value === null || value === undefined || value === '') {
    return 'Unknown';
  }
  const numeric = Number(value);
  if (!Number.isNaN(numeric) && numeric > 1000) {
    return formatTimestamp(numeric * 1000);
  }
  return String(value);
}

function absoluteUrl(baseUrl, path) {
  if (!path) {
    return '';
  }
  if (/^https?:\/\//i.test(path)) {
    return path;
  }
  return `${normalizeBaseUrl(baseUrl)}${path.startsWith('/') ? '' : '/'}${path}`;
}

function inferDashboardUrl() {
  const scriptUrl = NativeModules?.SourceCode?.scriptURL || '';
  const match = scriptUrl.match(/^https?:\/\/([^/:]+)(?::\d+)?/i);
  if (!match) {
    return '';
  }
  return `http://${match[1]}:8080`;
}

async function getOrCreateDeviceId() {
  const existing = await AsyncStorage.getItem(DEVICE_ID_KEY);
  if (existing) {
    return existing;
  }
  const created = `mobile-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
  await AsyncStorage.setItem(DEVICE_ID_KEY, created);
  return created;
}

function appLaunchCandidates(name, payload = {}) {
  const app = String(name || payload.app || payload.name || '').trim().toLowerCase();
  const customUrl = String(payload.url || payload.deepLink || '').trim();
  if (customUrl) {
    return [customUrl];
  }
  const map = {
    chrome: ['googlechrome://', 'https://www.google.com'],
    browser: ['https://www.google.com'],
    youtube: ['youtube://', 'https://www.youtube.com'],
    spotify: ['spotify://', 'https://open.spotify.com'],
    whatsapp: ['whatsapp://', 'https://wa.me'],
    telegram: ['tg://resolve', 'https://t.me'],
    instagram: ['instagram://', 'https://www.instagram.com'],
    gmail: ['googlegmail://', 'mailto:'],
    maps: ['geo:0,0?q=', 'https://maps.google.com'],
    phone: ['tel:'],
    sms: ['sms:'],
    settings: ['app-settings:'],
  };
  return map[app] || [];
}

function buildDeviceCapabilities(androidAgentStatus) {
  const nativeCapabilities = Array.isArray(androidAgentStatus?.supportedActions)
    ? androidAgentStatus.supportedActions.map((action) => `android_agent:${action}`)
    : [];
  return [
    ...BASE_MOBILE_CAPABILITIES,
    ...(androidAgentStatus?.available ? ['native_android_agent'] : ['native_android_agent_unavailable']),
    ...nativeCapabilities,
  ];
}

function extractIpv4Host(url) {
  const match = normalizeBaseUrl(url).match(/^https?:\/\/(\d{1,3}(?:\.\d{1,3}){3})(?::\d+)?$/i);
  return match ? match[1] : '';
}

function subnetCandidates(host) {
  if (!host || !/^(\d{1,3}\.){3}\d{1,3}$/.test(host)) {
    return [];
  }
  const parts = host.split('.');
  const prefix = parts.slice(0, 3).join('.');
  const preferred = Number(parts[3]);
  const ips = [];
  for (let i = 1; i <= 254; i += 1) {
    if (i === preferred) {
      continue;
    }
    ips.push(`${prefix}.${i}`);
  }
  return [`${prefix}.${preferred}`, ...ips];
}

async function fetchJsonWithTimeout(url, options = {}, timeoutMs = 900) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, { ...options, signal: controller.signal });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || `Request failed: ${response.status}`);
    }
    return data;
  } finally {
    clearTimeout(timer);
  }
}

function MetricCard({ label, value, tone }) {
  const toneStyle =
    tone === 'cyan'
      ? styles.metricCyan
      : tone === 'amber'
        ? styles.metricAmber
        : tone === 'green'
          ? styles.metricGreen
          : styles.metricBlue;

  return (
    <View style={[styles.metricCard, toneStyle]}>
      <Text style={styles.metricValue}>{value}</Text>
      <Text style={styles.metricLabel}>{label}</Text>
    </View>
  );
}

function SectionTitle({ eyebrow, title, body }) {
  return (
    <View style={styles.sectionHeader}>
      <Text style={styles.sectionEyebrow}>{eyebrow}</Text>
      <Text style={styles.sectionTitle}>{title}</Text>
      {!!body && <Text style={styles.sectionBody}>{body}</Text>}
    </View>
  );
}

function EmptyState({ title, body }) {
  return (
    <View style={styles.emptyState}>
      <Text style={styles.emptyTitle}>{title}</Text>
      <Text style={styles.emptyBody}>{body}</Text>
    </View>
  );
}

function ConnectionGate({
  baseUrl,
  password,
  userId,
  onChange,
  onReload,
  onAutoDetect,
  loading,
  detecting,
  error,
  detectedUrl,
  lastSyncedAt,
}) {
  return (
    <View style={styles.panel}>
      <View style={styles.connectionHero}>
        <Image source={MASCOT} style={styles.connectionMascot} resizeMode="contain" />
        <View style={styles.connectionCopy}>
          <Text style={styles.panelTitle}>Connect to your dashboard</Text>
          <Text style={styles.panelBody}>
            Enter your Ninoclaw dashboard LAN URL, dashboard password, and a mobile chat user id.
          </Text>
          {!!detectedUrl && !baseUrl && (
            <Text style={styles.helperText}>Suggested from this device: {detectedUrl}</Text>
          )}
          {!!lastSyncedAt && (
            <Text style={styles.helperText}>Last sync: {formatTimestamp(lastSyncedAt)}</Text>
          )}
        </View>
      </View>

      <TextInput
        value={baseUrl}
        onChangeText={(value) => onChange('baseUrl', value)}
        placeholder="http://192.168.x.x:8080"
        placeholderTextColor={COLORS.muted}
        style={styles.input}
        autoCapitalize="none"
      />
      <TextInput
        value={password}
        onChangeText={(value) => onChange('password', value)}
        placeholder="Dashboard password"
        placeholderTextColor={COLORS.muted}
        style={styles.input}
        autoCapitalize="none"
        secureTextEntry
      />
      <TextInput
        value={userId}
        onChangeText={(value) => onChange('userId', value)}
        placeholder="mobile"
        placeholderTextColor={COLORS.muted}
        style={styles.input}
        autoCapitalize="none"
      />

      {!!error && <Text style={styles.errorText}>{error}</Text>}

      <TouchableOpacity
        style={[styles.secondaryButton, detecting && styles.buttonDisabled, { marginBottom: 10 }]}
        onPress={onAutoDetect}
        disabled={loading || detecting}
      >
        <Text style={styles.secondaryButtonText}>
          {detecting ? 'Scanning local network...' : 'Auto-detect on LAN'}
        </Text>
      </TouchableOpacity>

      <TouchableOpacity style={styles.primaryButton} onPress={onReload} disabled={loading}>
        <Text style={styles.primaryButtonText}>{loading ? 'Connecting...' : 'Load live data'}</Text>
      </TouchableOpacity>
    </View>
  );
}

// ─── helpers ────────────────────────────────────────────────────────────────

function isSameDay(a, b) {
  const da = new Date(a);
  const db = new Date(b);
  return da.getFullYear() === db.getFullYear() &&
    da.getMonth() === db.getMonth() &&
    da.getDate() === db.getDate();
}

function dayLabel(ts) {
  const d = new Date(ts);
  const today = new Date();
  const yesterday = new Date(today);
  yesterday.setDate(today.getDate() - 1);
  if (isSameDay(d, today)) return 'Today';
  if (isSameDay(d, yesterday)) return 'Yesterday';
  return d.toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' });
}

function msgTime(ts) {
  if (!ts) return '';
  return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

// ─── ReplyBar ───────────────────────────────────────────────────────────────

function ReplyBar({ message, onCancel }) {
  if (!message) return null;
  const preview = message.type === 'image' ? '📷 Photo' :
    message.type === 'file' ? `📎 ${message.fileName || 'File'}` :
    message.type === 'audio' ? '🎤 Voice message' :
    (message.content || '').slice(0, 60);
  return (
    <View style={tgStyles.replyBar}>
      <View style={tgStyles.replyBarAccent} />
      <View style={{ flex: 1 }}>
        <Text style={tgStyles.replyBarFrom}>{message.role === 'user' ? 'You' : 'Ninoclaw'}</Text>
        <Text style={tgStyles.replyBarText} numberOfLines={1}>{preview}</Text>
      </View>
      <TouchableOpacity onPress={onCancel} style={tgStyles.replyBarClose}>
        <Text style={{ color: COLORS.muted, fontSize: 18, lineHeight: 20 }}>×</Text>
      </TouchableOpacity>
    </View>
  );
}

// ─── AttachMenu ─────────────────────────────────────────────────────────────

function AttachMenu({ visible, onClose, onCamera, onGallery, onFile }) {
  if (!visible) return null;
  const options = [
    { icon: 'camera-outline', label: 'Camera', onPress: onCamera },
    { icon: 'images-outline', label: 'Gallery', onPress: onGallery },
    { icon: 'document-outline', label: 'File', onPress: onFile },
  ];
  return (
    <View style={tgStyles.attachMenu}>
      {options.map((o) => (
        <TouchableOpacity key={o.label} style={tgStyles.attachOption} onPress={() => { onClose(); o.onPress(); }}>
          <View style={tgStyles.attachIconWrap}>
            <Ionicons name={o.icon} size={26} color="#4fc3f7" />
          </View>
          <Text style={tgStyles.attachLabel}>{o.label}</Text>
        </TouchableOpacity>
      ))}
    </View>
  );
}

// ─── ContextMenu ────────────────────────────────────────────────────────────

function ContextMenu({ message, position, onClose, onReply, onCopy, onDelete }) {
  if (!message) return null;
  const actions = [
    { label: '↩ Reply', onPress: onReply },
    ...(message.type === 'text' ? [{ label: '📋 Copy', onPress: onCopy }] : []),
    { label: '🗑 Delete', onPress: onDelete, danger: true },
  ];
  return (
    <Modal transparent animationType="fade" onRequestClose={onClose}>
      <Pressable style={tgStyles.ctxOverlay} onPress={onClose}>
        <View style={[tgStyles.ctxMenu, { top: Math.min(position.y, 400), left: position.x > 200 ? undefined : position.x, right: position.x > 200 ? 16 : undefined }]}>
          {actions.map((a) => (
            <TouchableOpacity key={a.label} style={tgStyles.ctxItem} onPress={() => { onClose(); a.onPress(); }}>
              <Text style={[tgStyles.ctxItemText, a.danger && { color: COLORS.coral }]}>{a.label}</Text>
            </TouchableOpacity>
          ))}
        </View>
      </Pressable>
    </Modal>
  );
}

// ─── MessageBubble ──────────────────────────────────────────────────────────

function MessageBubble({ message, prevMessage, onLongPress }) {
  const isUser = message.role === 'user';
  const showDay = !prevMessage || !isSameDay(message.ts, prevMessage.ts);

  const renderContent = () => {
    if (message.type === 'image') {
      return (
        <View>
          <Image source={{ uri: message.uri }} style={tgStyles.msgImage} resizeMode="cover" />
          {!!message.content && <Text style={tgStyles.msgText}>{message.content}</Text>}
        </View>
      );
    }
    if (message.type === 'file') {
      return (
        <View style={tgStyles.fileRow}>
          <Text style={{ fontSize: 24, marginRight: 10 }}>📎</Text>
          <View style={{ flex: 1 }}>
            <Text style={tgStyles.fileName} numberOfLines={1}>{message.fileName || 'File'}</Text>
            {!!message.fileSize && <Text style={tgStyles.fileSize}>{message.fileSize}</Text>}
          </View>
        </View>
      );
    }
    if (message.type === 'audio') {
      return (
        <View style={tgStyles.audioRow}>
          <Text style={{ fontSize: 22, marginRight: 8 }}>🎤</Text>
          <View style={tgStyles.audioBar}>
            <View style={tgStyles.audioWave} />
          </View>
          <Text style={[tgStyles.msgMeta, { marginLeft: 8, marginBottom: 0 }]}>{message.duration || '0:00'}</Text>
        </View>
      );
    }
    return <Text style={tgStyles.msgText}>{message.content}</Text>;
  };

  return (
    <View>
      {showDay && (
        <View style={tgStyles.dayPill}>
          <Text style={tgStyles.dayPillText}>{dayLabel(message.ts)}</Text>
        </View>
      )}
      {!!message.replyTo && (
        <View style={[tgStyles.msgReplyPreview, isUser ? { alignSelf: 'flex-end' } : { alignSelf: 'flex-start', marginLeft: 8 }]}>
          <View style={tgStyles.msgReplyAccent} />
          <View>
            <Text style={tgStyles.msgReplyFrom}>{message.replyTo.role === 'user' ? 'You' : 'Ninoclaw'}</Text>
            <Text style={tgStyles.msgReplyText} numberOfLines={1}>
              {message.replyTo.type === 'image' ? '📷 Photo' : (message.replyTo.content || '').slice(0, 40)}
            </Text>
          </View>
        </View>
      )}
      <Pressable
        onLongPress={(e) => onLongPress(message, e.nativeEvent)}
        style={[tgStyles.msgRow, isUser ? tgStyles.msgRowUser : tgStyles.msgRowAssistant]}
      >
        {!isUser && (
          <View style={tgStyles.avatarCircle}>
            <Text style={{ fontSize: 15 }}>🦀</Text>
          </View>
        )}
        <View style={[tgStyles.bubble, isUser ? tgStyles.bubbleUser : tgStyles.bubbleAssistant]}>
          {renderContent()}
          <View style={tgStyles.msgMetaRow}>
            <Text style={tgStyles.msgMeta}>{msgTime(message.ts)}</Text>
            {isUser && <Text style={tgStyles.msgStatus}>{message.status === 'sent' ? ' ✓' : ' ✓✓'}</Text>}
          </View>
        </View>
      </Pressable>
    </View>
  );
}

// ─── VoiceButton ────────────────────────────────────────────────────────────

function VoiceButton({ onRecorded }) {
  const [recording, setRecording] = useState(false);
  const recorder = useAudioRecorder(RecordingPresets.HIGH_QUALITY);
  const scaleAnim = useRef(new Animated.Value(1)).current;

  async function startRecord() {
    try {
      const { granted } = await requestMicrophonePermissionsAsync();
      if (!granted) { Alert.alert('Permission required', 'Microphone access needed for voice messages.'); return; }
      await recorder.record();
      setRecording(true);
      Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
      Animated.loop(Animated.sequence([
        Animated.timing(scaleAnim, { toValue: 1.3, duration: 500, useNativeDriver: true }),
        Animated.timing(scaleAnim, { toValue: 1, duration: 500, useNativeDriver: true }),
      ])).start();
    } catch (_e) {}
  }

  async function stopRecord() {
    if (!recording) return;
    try {
      scaleAnim.stopAnimation();
      Animated.timing(scaleAnim, { toValue: 1, duration: 100, useNativeDriver: true }).start();
      await recorder.stop();
      const uri = recorder.uri;
      setRecording(false);
      Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
      if (uri) onRecorded(uri);
    } catch (_e) { setRecording(false); }
  }

  return (
    <Animated.View style={{ transform: [{ scale: scaleAnim }] }}>
      <TouchableOpacity
        style={[tgStyles.voiceBtn, recording && tgStyles.voiceBtnActive]}
        onPressIn={startRecord}
        onPressOut={stopRecord}
        activeOpacity={0.8}
      >
        <Text style={{ fontSize: 20 }}>🎤</Text>
      </TouchableOpacity>
    </Animated.View>
  );
}

// ─── EmojiPicker ────────────────────────────────────────────────────────────

const QUICK_EMOJIS = ['😊','😂','❤️','👍','🔥','✅','🎉','😎','🤔','👀','💯','🙏','😅','🚀','💪','🎯','⚡','🤖','🦀','✨'];

function EmojiPicker({ visible, onSelect, onClose }) {
  if (!visible) return null;
  return (
    <View style={tgStyles.emojiPicker}>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ paddingHorizontal: 8 }}>
        {QUICK_EMOJIS.map((e) => (
          <TouchableOpacity key={e} onPress={() => onSelect(e)} style={tgStyles.emojiBtn}>
            <Text style={{ fontSize: 24 }}>{e}</Text>
          </TouchableOpacity>
        ))}
      </ScrollView>
    </View>
  );
}

// ─── ChatScreen ─────────────────────────────────────────────────────────────

function ChatScreen({ chatMessages, draft, setDraft, onSend, onSendMedia, sending, userId, overview, onBack, setActiveTab, activeTab }) {
  const flatRef = useRef(null);
  const [replyTo, setReplyTo] = useState(null);
  const [contextMsg, setContextMsg] = useState(null);
  const [contextPos, setContextPos] = useState({ x: 0, y: 0 });
  const [showAttach, setShowAttach] = useState(false);
  const [showEmoji, setShowEmoji] = useState(false);
  const [pendingMedia, setPendingMedia] = useState(null); // { type, uri, base64, fileName, fileSize }
  const isOnline = !!overview;

  useEffect(() => {
    if (chatMessages.length > 0) {
      setTimeout(() => flatRef.current?.scrollToEnd({ animated: true }), 100);
    }
  }, [chatMessages.length]);

  function handleLongPress(msg, nativeEvent) {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    setContextMsg(msg);
    setContextPos({ x: nativeEvent.pageX, y: nativeEvent.pageY });
  }

  async function handleCopy() {
    if (contextMsg?.content) {
      await Clipboard.setStringAsync(contextMsg.content);
    }
  }

  async function pickFromCamera() {
    const { status } = await ImagePicker.requestCameraPermissionsAsync();
    if (status !== 'granted') { Alert.alert('Permission required', 'Camera access needed.'); return; }
    const result = await ImagePicker.launchCameraAsync({ mediaTypes: ['images'], quality: 0.7, base64: true });
    if (!result.canceled && result.assets[0]) {
      const asset = result.assets[0];
      setPendingMedia({ type: 'image', uri: asset.uri, base64: asset.base64 });
    }
  }

  async function pickFromGallery() {
    const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (status !== 'granted') { Alert.alert('Permission required', 'Photo library access needed.'); return; }
    const result = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ['images'], quality: 0.7, base64: true, allowsMultipleSelection: false });
    if (!result.canceled && result.assets[0]) {
      const asset = result.assets[0];
      setPendingMedia({ type: 'image', uri: asset.uri, base64: asset.base64 });
    }
  }

  async function pickFile() {
    try {
      const result = await DocumentPicker.getDocumentAsync({ copyToCacheDirectory: true });
      if (!result.canceled && result.assets[0]) {
        const asset = result.assets[0];
        setPendingMedia({ type: 'file', uri: asset.uri, fileName: asset.name, fileSize: asset.size ? `${(asset.size / 1024).toFixed(1)} KB` : '' });
      }
    } catch (_e) {}
  }

  function handleSend() {
    const text = draft.trim();
    if (!text && !pendingMedia) return;
    if (pendingMedia) {
      onSendMedia({ ...pendingMedia, content: text, replyTo });
      setPendingMedia(null);
    } else {
      onSend(text, replyTo);
    }
    setDraft('');
    setReplyTo(null);
    setShowEmoji(false);
  }

  function handleVoice(uri) {
    onSendMedia({ type: 'audio', uri, replyTo });
    setReplyTo(null);
  }

  const hasDraft = draft.trim().length > 0;

  const TABS_BAR = (
    <View style={tgStyles.tabBar}>
      {TABS.map((tab) => {
        const isActive = tab.key === activeTab;
        return (
          <TouchableOpacity key={tab.key} onPress={() => setActiveTab(tab.key)} style={tgStyles.tabBtn}>
            <Text style={[tgStyles.tabText, isActive && tgStyles.tabTextActive]}>{tab.label}</Text>
            <View style={[tgStyles.tabIndicator, isActive && tgStyles.tabIndicatorActive]} />
          </TouchableOpacity>
        );
      })}
    </View>
  );

  return (
    <View style={tgStyles.screen}>
      {/* Header */}
      <View style={tgStyles.header}>
        <Image source={MASCOT} style={tgStyles.headerAvatar} resizeMode="contain" />
        <View style={{ flex: 1 }}>
          <Text style={tgStyles.headerName}>Ninoclaw</Text>
          <Text style={[tgStyles.headerSub, isOnline && { color: '#4fc3f7' }]}>{isOnline ? 'online' : 'offline'}</Text>
        </View>
        <View style={[tgStyles.onlineDot, isOnline && { backgroundColor: '#4caf50' }]} />
      </View>

      {/* Messages */}
      <FlatList
        ref={flatRef}
        data={chatMessages}
        keyExtractor={(item, i) => `${item.role}-${i}-${item.ts || i}`}
        renderItem={({ item, index }) => (
          <MessageBubble
            message={item}
            prevMessage={index > 0 ? chatMessages[index - 1] : null}
            onLongPress={handleLongPress}
          />
        )}
        contentContainerStyle={tgStyles.messageList}
        ListEmptyComponent={
          <View style={tgStyles.emptyChat}>
            <Image source={MASCOT} style={{ width: 80, height: 80, opacity: 0.4, marginBottom: 16 }} resizeMode="contain" />
            <Text style={tgStyles.emptyChatText}>Send a message to start chatting with Ninoclaw</Text>
          </View>
        }
        onContentSizeChange={() => flatRef.current?.scrollToEnd({ animated: false })}
      />

      {/* Emoji picker */}
      <EmojiPicker visible={showEmoji} onSelect={(e) => setDraft((d) => d + e)} onClose={() => setShowEmoji(false)} />

      {/* Attach menu */}
      <AttachMenu visible={showAttach} onClose={() => setShowAttach(false)} onCamera={pickFromCamera} onGallery={pickFromGallery} onFile={pickFile} />

      {/* Pending media preview */}
      {!!pendingMedia && (
        <View style={tgStyles.pendingBar}>
          {pendingMedia.type === 'image' ? (
            <Image source={{ uri: pendingMedia.uri }} style={tgStyles.pendingThumb} />
          ) : (
            <View style={tgStyles.pendingFileIcon}>
              <Ionicons name="document-outline" size={22} color="#4fc3f7" />
            </View>
          )}
          <View style={{ flex: 1 }}>
            <Text style={tgStyles.pendingLabel} numberOfLines={1}>
              {pendingMedia.type === 'image' ? 'Photo' : pendingMedia.fileName}
            </Text>
            <Text style={tgStyles.pendingHint}>Add a caption and tap send</Text>
          </View>
          <TouchableOpacity onPress={() => setPendingMedia(null)} style={{ padding: 6 }}>
            <Ionicons name="close-circle" size={22} color={COLORS.muted} />
          </TouchableOpacity>
        </View>
      )}

      {/* Reply bar */}
      <ReplyBar message={replyTo} onCancel={() => setReplyTo(null)} />

      {/* Composer */}
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} keyboardVerticalOffset={0}>
        <View style={tgStyles.composer}>
          <TouchableOpacity style={tgStyles.composerBtn} onPress={() => { setShowEmoji((v) => !v); setShowAttach(false); }}>
            <Ionicons name={showEmoji ? 'keypad-outline' : 'happy-outline'} size={24} color={COLORS.muted} />
          </TouchableOpacity>
          <TextInput
            value={draft}
            onChangeText={setDraft}
            placeholder={pendingMedia ? 'Add a caption...' : 'Message...'}
            placeholderTextColor={COLORS.muted}
            style={tgStyles.composerInput}
            multiline
            maxHeight={120}
            onFocus={() => { setShowEmoji(false); setShowAttach(false); }}
          />
          {!pendingMedia && (
            <TouchableOpacity style={tgStyles.composerBtn} onPress={() => { setShowAttach((v) => !v); setShowEmoji(false); }}>
              <Ionicons name="attach" size={24} color={COLORS.muted} />
            </TouchableOpacity>
          )}
          {(hasDraft || pendingMedia) ? (
            <TouchableOpacity style={[tgStyles.sendBtn, sending && { opacity: 0.5 }]} onPress={handleSend} disabled={sending}>
              {sending
                ? <ActivityIndicator size="small" color="#fff" />
                : <Ionicons name="send" size={18} color="#fff" />}
            </TouchableOpacity>
          ) : (
            <VoiceButton onRecorded={handleVoice} />
          )}
        </View>
      </KeyboardAvoidingView>

      {/* Bottom tabs */}
      {TABS_BAR}

      {/* Context menu */}
      <ContextMenu
        message={contextMsg}
        position={contextPos}
        onClose={() => setContextMsg(null)}
        onReply={() => { setReplyTo(contextMsg); setContextMsg(null); }}
        onCopy={handleCopy}
        onDelete={() => {
          Alert.alert('Delete', 'Remove this message from local view?', [
            { text: 'Cancel', style: 'cancel' },
            { text: 'Delete', style: 'destructive', onPress: () => setContextMsg(null) },
          ]);
        }}
      />
    </View>
  );
}

function TasksTab({
  taskData,
  reminderName,
  setReminderName,
  reminderWhen,
  setReminderWhen,
  cronName,
  setCronName,
  cronExpression,
  setCronExpression,
  cronCommand,
  setCronCommand,
  onCreateReminder,
  onCreateCron,
  onCompleteTask,
  onDeleteTask,
  onToggleCron,
  onDeleteCron,
  onEditTask,
  onEditCron,
  editingTaskId,
  editingCronId,
  onCancelTaskEdit,
  onCancelCronEdit,
  actionBusy,
}) {
  const tasks = taskData?.tasks || [];
  const crons = taskData?.crons || [];

  return (
    <View>
      <SectionTitle
        eyebrow="Automation"
        title="Live reminders and cron jobs"
        body="This pulls directly from the SQLite-backed task system behind the dashboard."
      />

      <View style={styles.panel}>
        <Text style={styles.panelTitle}>{editingTaskId ? 'Edit reminder' : 'Create reminder'}</Text>
        <Text style={styles.helperText}>Examples: `in 20 minutes`, `in 2 hours`, `in 1 day`</Text>
        <TextInput
          value={reminderName}
          onChangeText={setReminderName}
          placeholder="Call mom"
          placeholderTextColor={COLORS.muted}
          style={styles.input}
        />
        <TextInput
          value={reminderWhen}
          onChangeText={setReminderWhen}
          placeholder="in 20 minutes"
          placeholderTextColor={COLORS.muted}
          style={styles.input}
        />
        <TouchableOpacity
          style={[styles.primaryButton, actionBusy === 'create-reminder' && styles.buttonDisabled]}
          onPress={onCreateReminder}
          disabled={!!actionBusy}
        >
          <Text style={styles.primaryButtonText}>
            {actionBusy === 'create-reminder' ? 'Saving...' : editingTaskId ? 'Save reminder' : 'Create reminder'}
          </Text>
        </TouchableOpacity>
        {!!editingTaskId && (
          <TouchableOpacity style={styles.ghostButton} onPress={onCancelTaskEdit} disabled={!!actionBusy}>
            <Text style={styles.ghostButtonText}>Cancel edit</Text>
          </TouchableOpacity>
        )}
      </View>

      <View style={styles.panel}>
        <Text style={styles.panelTitle}>{editingCronId ? 'Edit recurring task' : 'Create recurring task'}</Text>
        <Text style={styles.helperText}>Examples: `every day at 8am`, `every 2 hours`, `weekdays at 9am`</Text>
        <TextInput
          value={cronName}
          onChangeText={setCronName}
          placeholder="Morning summary"
          placeholderTextColor={COLORS.muted}
          style={styles.input}
        />
        <TextInput
          value={cronExpression}
          onChangeText={setCronExpression}
          placeholder="every day at 8am"
          placeholderTextColor={COLORS.muted}
          style={styles.input}
        />
        <TextInput
          value={cronCommand}
          onChangeText={setCronCommand}
          placeholder="Send me my agenda and top priorities"
          placeholderTextColor={COLORS.muted}
          style={styles.input}
          multiline
        />
        <TouchableOpacity
          style={[styles.primaryButton, actionBusy === 'create-cron' && styles.buttonDisabled]}
          onPress={onCreateCron}
          disabled={!!actionBusy}
        >
          <Text style={styles.primaryButtonText}>
            {actionBusy === 'create-cron' ? 'Saving...' : editingCronId ? 'Save recurring task' : 'Create recurring task'}
          </Text>
        </TouchableOpacity>
        {!!editingCronId && (
          <TouchableOpacity style={styles.ghostButton} onPress={onCancelCronEdit} disabled={!!actionBusy}>
            <Text style={styles.ghostButtonText}>Cancel edit</Text>
          </TouchableOpacity>
        )}
      </View>

      <View style={styles.panel}>
        <Text style={styles.panelTitle}>Pending reminders</Text>
        {tasks.length ? (
          tasks.map((task) => (
            <View key={task.id} style={styles.rowCard}>
              <View style={styles.rowMain}>
                <Text style={styles.rowTitle}>{task.name}</Text>
                <Text style={styles.rowMeta}>
                  {task.user_id} · {formatScheduledTime(task.scheduled_time)}
                </Text>
              </View>
              <View style={styles.rowActions}>
                <View style={[styles.badge, task.completed ? styles.badgeMuted : null]}>
                  <Text style={styles.badgeText}>{task.completed ? 'Done' : 'Pending'}</Text>
                </View>
                <TouchableOpacity
                  style={[styles.secondaryButton, actionBusy === `done-task:${task.id}` && styles.buttonDisabled]}
                  onPress={() => onCompleteTask(task.id)}
                  disabled={!!actionBusy || task.completed}
                >
                  <Text style={styles.secondaryButtonText}>
                    {actionBusy === `done-task:${task.id}` ? 'Saving...' : 'Done'}
                  </Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={styles.secondaryButton}
                  onPress={() => onEditTask(task)}
                  disabled={!!actionBusy}
                >
                  <Text style={styles.secondaryButtonText}>Edit</Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={[styles.secondaryButton, actionBusy === `delete-task:${task.id}` && styles.buttonDisabled]}
                  onPress={() => onDeleteTask(task.id)}
                  disabled={!!actionBusy}
                >
                  <Text style={styles.secondaryButtonText}>
                    {actionBusy === `delete-task:${task.id}` ? 'Deleting...' : 'Delete'}
                  </Text>
                </TouchableOpacity>
              </View>
            </View>
          ))
        ) : (
          <EmptyState title="No reminder tasks" body="New reminders will appear here when they are scheduled." />
        )}
      </View>

      <View style={styles.panel}>
        <Text style={styles.panelTitle}>Recurring jobs</Text>
        {crons.length ? (
          crons.map((job) => (
            <View key={job.id} style={styles.rowCard}>
              <View style={styles.rowMain}>
                <Text style={styles.rowTitle}>{job.name}</Text>
                <Text style={styles.rowMeta}>
                  {job.user_id} · {job.cron_expression}
                </Text>
              </View>
              <View style={styles.rowActions}>
                <View style={[styles.badge, !job.is_active ? styles.badgeMuted : null]}>
                  <Text style={styles.badgeText}>{job.is_active ? 'Active' : 'Paused'}</Text>
                </View>
                <TouchableOpacity
                  style={[styles.secondaryButton, actionBusy === `toggle-cron:${job.id}` && styles.buttonDisabled]}
                  onPress={() => onToggleCron(job.id, job.user_id)}
                  disabled={!!actionBusy}
                >
                  <Text style={styles.secondaryButtonText}>
                    {actionBusy === `toggle-cron:${job.id}` ? 'Saving...' : job.is_active ? 'Pause' : 'Resume'}
                  </Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={styles.secondaryButton}
                  onPress={() => onEditCron(job)}
                  disabled={!!actionBusy}
                >
                  <Text style={styles.secondaryButtonText}>Edit</Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={[styles.secondaryButton, actionBusy === `delete-cron:${job.id}` && styles.buttonDisabled]}
                  onPress={() => onDeleteCron(job.id, job.user_id)}
                  disabled={!!actionBusy}
                >
                  <Text style={styles.secondaryButtonText}>
                    {actionBusy === `delete-cron:${job.id}` ? 'Deleting...' : 'Delete'}
                  </Text>
                </TouchableOpacity>
              </View>
            </View>
          ))
        ) : (
          <EmptyState title="No cron jobs" body="Recurring schedules from Ninoclaw will show up here." />
        )}
      </View>
    </View>
  );
}

function BuildsTab({ baseUrl, buildsData, mobileAppsData, onExpoAction, actionBusy }) {
  const projects = buildsData?.projects || [];
  const apps = mobileAppsData?.apps || [];

  return (
    <View>
      <SectionTitle
        eyebrow="Output"
        title="Live builds and Expo apps"
        body="Website projects and mobile apps now come from your real local build inventory."
      />

      <View style={styles.panel}>
        <Text style={styles.panelTitle}>Generated websites</Text>
        {projects.length ? (
          projects.map((project) => (
            <View key={project.name} style={styles.buildCard}>
              <View style={styles.buildTop}>
                <Text style={styles.buildName}>{project.name}</Text>
                <Text style={styles.buildStatus}>{project.modified}</Text>
              </View>
              <Text style={styles.buildType}>{project.size_label}</Text>
              <Text style={styles.buildDetail}>{absoluteUrl(baseUrl, project.preview_url)}</Text>
            </View>
          ))
        ) : (
          <EmptyState title="No builds yet" body="Generated websites from the builder will appear here." />
        )}
      </View>

      <View style={styles.panel}>
        <Text style={styles.panelTitle}>Expo apps</Text>
        {apps.length ? (
          apps.map((app) => (
            <View key={app.name} style={styles.buildCard}>
              <View style={styles.buildTop}>
                <Text style={styles.buildName}>{app.name}</Text>
                <Text style={styles.buildStatus}>{app.is_running ? 'Running' : 'Stopped'}</Text>
              </View>
              <Text style={styles.buildType}>{app.template || 'blank'}</Text>
              <Text style={styles.buildDetail}>
                {app.web_url || app.launch_url || app.tunnel_url || 'No preview URL available yet'}
              </Text>
              <View style={styles.buildActions}>
                <TouchableOpacity
                  style={[styles.secondaryButton, actionBusy === `start:${app.name}` && styles.buttonDisabled]}
                  onPress={() => onExpoAction(app.name, 'start')}
                  disabled={!!actionBusy}
                >
                  <Text style={styles.secondaryButtonText}>
                    {actionBusy === `start:${app.name}` ? 'Starting...' : 'Start'}
                  </Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={[styles.secondaryButton, actionBusy === `stop:${app.name}` && styles.buttonDisabled]}
                  onPress={() => onExpoAction(app.name, 'stop')}
                  disabled={!!actionBusy}
                >
                  <Text style={styles.secondaryButtonText}>
                    {actionBusy === `stop:${app.name}` ? 'Stopping...' : 'Stop'}
                  </Text>
                </TouchableOpacity>
              </View>
            </View>
          ))
        ) : (
          <EmptyState title="No Expo apps yet" body="Expo apps managed by Ninoclaw will show up here." />
        )}
      </View>
    </View>
  );
}

function SettingsTab({
  baseUrl,
  password,
  userId,
  onChange,
  onReload,
  loading,
  settingsData,
  runtimeHealth,
  overview,
  error,
  detectedUrl,
  lastSyncedAt,
  modelPrimary,
  setModelPrimary,
  modelFast,
  setModelFast,
  modelSmart,
  setModelSmart,
  onSaveModels,
  onTogglePlugin,
  onReloadRuntime,
  onFixEnv,
  actionBusy,
  onToggleMobileControl,
  androidAgentStatus,
  onRefreshAndroidAgent,
  onOpenAccessibilitySettings,
  executorTasks,
  executorLog,
}) {
  const pluginEntries = Object.entries(settingsData?.plugins || {});
  const mobileControl = settingsData?.mobile_control || { enabled: false, devices: [] };
  const nativeAgent = androidAgentStatus || {};

  return (
    <View>
      <SectionTitle
        eyebrow="Runtime"
        title="Connection, models, and toggles"
        body="This tab is fully live and doubles as the control point for connecting the app to your local dashboard."
      />

      <ConnectionGate
        baseUrl={baseUrl}
        password={password}
        userId={userId}
        onChange={onChange}
        onReload={onReload}
        loading={loading}
        error={error}
        detectedUrl={detectedUrl}
        lastSyncedAt={lastSyncedAt}
      />

      <View style={styles.panel}>
        <Text style={styles.panelTitle}>Agent</Text>
        <View style={styles.settingRow}>
          <Text style={styles.settingTitle}>Bot name</Text>
          <Text style={styles.settingValue}>{settingsData?.agent?.name || 'Unavailable'}</Text>
        </View>
        <View style={styles.settingRow}>
          <Text style={styles.settingTitle}>User name</Text>
          <Text style={styles.settingValue}>{settingsData?.agent?.user_name || 'Unavailable'}</Text>
        </View>
        <View style={styles.settingRow}>
          <Text style={styles.settingTitle}>Timezone</Text>
          <Text style={styles.settingValue}>{settingsData?.agent?.timezone || 'Unavailable'}</Text>
        </View>
      </View>

      <View style={styles.panel}>
        <Text style={styles.panelTitle}>Mobile control</Text>
        <View style={styles.settingRow}>
          <Text style={styles.settingTitle}>Executor mode</Text>
          <TouchableOpacity
            style={[styles.secondaryButton, actionBusy === 'mobile-control' && styles.buttonDisabled]}
            onPress={() => onToggleMobileControl(!mobileControl.enabled)}
            disabled={!!actionBusy}
          >
            <Text style={styles.secondaryButtonText}>
              {actionBusy === 'mobile-control' ? 'Saving...' : mobileControl.enabled ? 'Enabled' : 'Disabled'}
            </Text>
          </TouchableOpacity>
        </View>
        <Text style={styles.helperText}>
          When enabled in the dashboard, trusted phones can evolve from companion app to task executor.
        </Text>
        {!!mobileControl.devices?.length && mobileControl.devices.map((device) => (
          <View key={device.device_id} style={styles.settingRow}>
            <Text style={styles.settingTitle}>{device.name || device.device_id}</Text>
            <Text style={styles.settingValue}>{device.status} · {device.platform}</Text>
          </View>
        ))}
        <View style={{ marginTop: 14 }}>
          <Text style={styles.panelTitle}>Executor inbox</Text>
          {executorTasks.length ? (
            executorTasks.map((task) => (
              <View key={task.id} style={styles.settingRow}>
                <Text style={styles.settingTitle}>{task.action}</Text>
                <Text style={styles.settingValue}>#{task.id} · {task.status}</Text>
              </View>
            ))
          ) : (
            <Text style={styles.helperText}>No queued mobile tasks right now.</Text>
          )}
        </View>
        <View style={{ marginTop: 14 }}>
          <Text style={styles.panelTitle}>Recent executor activity</Text>
          {executorLog.length ? (
            executorLog.map((item) => (
              <View key={item.id} style={styles.settingRow}>
                <Text style={styles.settingTitle}>{item.text}</Text>
                <Text style={styles.settingValue}>{formatTimestamp(item.at)}</Text>
              </View>
            ))
          ) : (
            <Text style={styles.helperText}>No executor actions have run on this device yet.</Text>
          )}
        </View>
      </View>

      <View style={styles.panel}>
        <Text style={styles.panelTitle}>Android agent</Text>
        <View style={styles.settingRow}>
          <Text style={styles.settingTitle}>Native bridge</Text>
          <Text style={styles.settingValue}>{nativeAgent.available ? 'Ready in custom build' : 'Unavailable in Expo Go'}</Text>
        </View>
        <View style={styles.settingRow}>
          <Text style={styles.settingTitle}>Accessibility service</Text>
          <Text style={styles.settingValue}>{nativeAgent.serviceEnabled ? 'Enabled' : 'Disabled'}</Text>
        </View>
        <View style={styles.settingRow}>
          <Text style={styles.settingTitle}>Tap and text input</Text>
          <Text style={styles.settingValue}>
            {nativeAgent.canTap || nativeAgent.canTypeText ? `${nativeAgent.canTap ? 'Tap' : ''}${nativeAgent.canTap && nativeAgent.canTypeText ? ' + ' : ''}${nativeAgent.canTypeText ? 'Type' : ''} ready` : 'Not ready'}
          </Text>
        </View>
        <View style={styles.settingRow}>
          <Text style={styles.settingTitle}>Last app</Text>
          <Text style={styles.settingValue}>{nativeAgent.lastPackageName || 'None yet'}</Text>
        </View>
        <Text style={styles.helperText}>
          Native Android control needs a custom dev build or APK. Expo Go can show the control plane, but it cannot load the accessibility module.
        </Text>
        {!!nativeAgent.supportedActions?.length && (
          <Text style={styles.helperText}>Supported native actions: {nativeAgent.supportedActions.join(', ')}</Text>
        )}
        <Text style={styles.helperText}>
          Selector tips: use payload keys like `viewId`, `text`, or `contentDescription`. For raw taps, send `x` and `y` screen coordinates.
        </Text>
        {!!nativeAgent.visibleTexts?.length && (
          <Text style={styles.helperText}>Latest visible text snapshot: {nativeAgent.visibleTexts.slice(0, 8).join(' | ')}</Text>
        )}
        {!!nativeAgent.setupSteps?.length && (
          <View style={{ marginTop: 8 }}>
            {nativeAgent.setupSteps.map((step, index) => (
              <Text key={`${index}-${step}`} style={styles.helperText}>{index + 1}. {step}</Text>
            ))}
          </View>
        )}
        <TouchableOpacity
          style={[styles.secondaryButton, actionBusy === 'refresh-android-agent' && styles.buttonDisabled, { marginTop: 12 }]}
          onPress={onRefreshAndroidAgent}
          disabled={!!actionBusy}
        >
          <Text style={styles.secondaryButtonText}>
            {actionBusy === 'refresh-android-agent' ? 'Refreshing...' : 'Refresh Android agent'}
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.secondaryButton, actionBusy === 'open-accessibility-settings' && styles.buttonDisabled, { marginTop: 10 }]}
          onPress={onOpenAccessibilitySettings}
          disabled={!!actionBusy}
        >
          <Text style={styles.secondaryButtonText}>
            {actionBusy === 'open-accessibility-settings' ? 'Opening...' : 'Open accessibility settings'}
          </Text>
        </TouchableOpacity>
      </View>

      <View style={styles.panel}>
        <Text style={styles.panelTitle}>Model routing</Text>
        <TextInput
          value={modelPrimary}
          onChangeText={setModelPrimary}
          placeholder="Primary model"
          placeholderTextColor={COLORS.muted}
          style={styles.input}
        />
        <TextInput
          value={modelFast}
          onChangeText={setModelFast}
          placeholder="Fast model (optional)"
          placeholderTextColor={COLORS.muted}
          style={styles.input}
        />
        <TextInput
          value={modelSmart}
          onChangeText={setModelSmart}
          placeholder="Smart model (optional)"
          placeholderTextColor={COLORS.muted}
          style={styles.input}
        />
        <TouchableOpacity
          style={[styles.primaryButton, actionBusy === 'save-models' && styles.buttonDisabled]}
          onPress={onSaveModels}
          disabled={!!actionBusy}
        >
          <Text style={styles.primaryButtonText}>
            {actionBusy === 'save-models' ? 'Saving...' : 'Save model settings'}
          </Text>
        </TouchableOpacity>
      </View>

      <View style={styles.panel}>
        <Text style={styles.panelTitle}>Plugins</Text>
        {pluginEntries.length ? (
          pluginEntries.map(([key, enabled]) => (
            <View key={key} style={styles.settingRow}>
              <Text style={styles.settingTitle}>{key.replace('ENABLE_', '').replaceAll('_', ' ')}</Text>
              <TouchableOpacity
                style={[styles.secondaryButton, actionBusy === `plugin:${key}` && styles.buttonDisabled]}
                onPress={() => onTogglePlugin(key, !enabled)}
                disabled={!!actionBusy}
              >
                <Text style={styles.secondaryButtonText}>
                  {actionBusy === `plugin:${key}` ? 'Saving...' : enabled ? 'On' : 'Off'}
                </Text>
              </TouchableOpacity>
            </View>
          ))
        ) : (
          <EmptyState title="No settings yet" body="Load live data to see your actual runtime toggles." />
        )}
      </View>

      <View style={styles.panel}>
        <Text style={styles.panelTitle}>Runtime actions</Text>
        <TouchableOpacity
          style={[styles.primaryButton, actionBusy === 'reload-runtime' && styles.buttonDisabled]}
          onPress={onReloadRuntime}
          disabled={!!actionBusy}
        >
          <Text style={styles.primaryButtonText}>
            {actionBusy === 'reload-runtime' ? 'Reloading...' : 'Reload runtime'}
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.secondaryButton, actionBusy === 'fixenv' && styles.buttonDisabled, { marginTop: 10 }]}
          onPress={onFixEnv}
          disabled={!!actionBusy}
        >
          <Text style={styles.secondaryButtonText}>
            {actionBusy === 'fixenv' ? 'Repairing...' : 'Fix environment'}
          </Text>
        </TouchableOpacity>
      </View>

      <View style={styles.panel}>
        <Text style={styles.panelTitle}>Environment health</Text>
        {runtimeHealth ? (
          Object.entries(runtimeHealth).map(([key, item]) => (
            <View key={key} style={styles.settingRow}>
              <Text style={styles.settingTitle}>{key.replaceAll('_', ' ')}</Text>
              <Text style={styles.settingValue}>{item?.ok ? 'OK' : item?.detail || 'Missing'}</Text>
            </View>
          ))
        ) : (
          <EmptyState title="No health data yet" body="Reload live data to inspect Python, Node, Expo, and Ollama." />
        )}
      </View>

      <View style={styles.panelSoft}>
        <Text style={styles.panelTitle}>System snapshot</Text>
        <Text style={styles.panelBody}>
          {overview?.system
            ? `${overview.system.os} · Python ${overview.system.python} · ${overview.system.disk_free_gb} GB free`
            : 'Connect to your dashboard to load system details.'}
        </Text>
        <Image source={MASCOT} style={styles.settingsMascot} resizeMode="contain" />
      </View>
    </View>
  );
}

export default function App() {
  const [activeTab, setActiveTab] = useState('chat');
  const [baseUrl, setBaseUrl] = useState('');
  const [password, setPassword] = useState('');
  const [userId, setUserId] = useState('mobile');
  const [draft, setDraft] = useState('');
  const [reminderName, setReminderName] = useState('');
  const [reminderWhen, setReminderWhen] = useState('');
  const [cronName, setCronName] = useState('');
  const [cronExpression, setCronExpression] = useState('');
  const [cronCommand, setCronCommand] = useState('');
  const [editingTaskId, setEditingTaskId] = useState('');
  const [editingCronId, setEditingCronId] = useState('');
  const [overview, setOverview] = useState(null);
  const [taskData, setTaskData] = useState(null);
  const [buildsData, setBuildsData] = useState(null);
  const [mobileAppsData, setMobileAppsData] = useState(null);
  const [settingsData, setSettingsData] = useState(null);
  const [runtimeHealth, setRuntimeHealth] = useState(null);
  const [chatMessages, setChatMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [sending, setSending] = useState(false);
  const [actionBusy, setActionBusy] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [bootstrapped, setBootstrapped] = useState(false);
  const [lastSyncedAt, setLastSyncedAt] = useState('');
  const [modelPrimary, setModelPrimary] = useState('');
  const [modelFast, setModelFast] = useState('');
  const [modelSmart, setModelSmart] = useState('');
  const [detectingDashboard, setDetectingDashboard] = useState(false);
  const [deviceId, setDeviceId] = useState('');
  const [androidAgentStatus, setAndroidAgentStatus] = useState(null);
  const [executorTasks, setExecutorTasks] = useState([]);
  const [executorLog, setExecutorLog] = useState([]);

  const headers = useMemo(
    () => ({
      'Content-Type': 'application/json',
      ...(password.trim() ? { 'X-Dashboard-Password': password.trim() } : {}),
    }),
    [password]
  );

  async function apiGet(path) {
    const response = await fetch(`${normalizeBaseUrl(baseUrl)}${path}`, {
      method: 'GET',
      headers,
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || `Request failed: ${response.status}`);
    }
    return data;
  }

  async function apiPost(path, body = {}) {
    const response = await fetch(`${normalizeBaseUrl(baseUrl)}${path}`, {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || `Request failed: ${response.status}`);
    }
    return data;
  }

  async function refreshAndroidAgentStatus() {
    const status = await getAndroidAgentStatus();
    setAndroidAgentStatus(status);
    return status;
  }

  async function registerMobileDevice(agentStatus = androidAgentStatus) {
    const id = deviceId || await getOrCreateDeviceId();
    if (!deviceId) {
      setDeviceId(id);
    }
    const ipAddress = await Network.getIpAddressAsync().catch(() => '');
    return apiPost('/api/mobile/device/register', {
      device_id: id,
      name: Platform.OS === 'android' ? 'Ninoclaw Android Companion' : 'Ninoclaw Mobile Companion',
      platform: Platform.OS,
      app_version: '1.0.0',
      capabilities: buildDeviceCapabilities(agentStatus),
      status: 'online',
      ip_address: ipAddress,
    });
  }

  function showSuccess(message) {
    setSuccess(message);
    setTimeout(() => {
      setSuccess((current) => (current === message ? '' : current));
    }, 2500);
  }

  async function loadAll(showSpinner = true) {
    if (!normalizeBaseUrl(baseUrl) || !password.trim() || !userId.trim()) {
      setError('Base URL, dashboard password, and user id are required.');
      return;
    }
    if (showSpinner) {
      setLoading(true);
    }
    setError('');
    try {
      const [overviewRes, taskRes, buildsRes, appsRes, settingsRes, chatRes, healthRes] = await Promise.all([
        apiGet('/api/mobile/overview'),
        apiGet('/api/mobile/tasks'),
        apiGet('/api/mobile/builds'),
        apiGet('/api/mobile/mobile-apps'),
        apiGet('/api/mobile/settings'),
        apiGet(`/api/mobile/chat/${encodeURIComponent(userId.trim())}`),
        apiGet('/api/mobile/runtime/health'),
      ]);
      setOverview(overviewRes);
      setTaskData(taskRes);
      setBuildsData(buildsRes);
      setMobileAppsData(appsRes);
      setSettingsData(settingsRes);
      setRuntimeHealth(healthRes);
      setChatMessages(chatRes.messages || []);
      setModelPrimary(settingsRes?.models?.primary || '');
      setModelFast(settingsRes?.models?.fast || '');
      setModelSmart(settingsRes?.models?.smart || '');
      try {
        const nativeStatus = await refreshAndroidAgentStatus();
        const registerRes = await registerMobileDevice(nativeStatus);
        if (registerRes?.mobile_control) {
          settingsRes.mobile_control = registerRes.mobile_control;
          setSettingsData({ ...settingsRes });
        }
      } catch (_registerError) {
      }
      setLastSyncedAt(new Date().toISOString());
    } catch (fetchError) {
      setError(fetchError.message || 'Failed to load live data.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  async function autoDetectDashboard() {
    setDetectingDashboard(true);
    setError('');
    setSuccess('');
    try {
      const inferredUrl = inferDashboardUrl();
      const currentHost = extractIpv4Host(baseUrl) || extractIpv4Host(inferredUrl);
      let deviceIp = '';
      try {
        deviceIp = await Network.getIpAddressAsync();
      } catch (_networkError) {
      }
      const hostSeed = extractIpv4Host(`http://${deviceIp}:8080`) || currentHost;
      if (!hostSeed) {
        throw new Error('Could not infer your LAN subnet. Enter the PC IP once, then auto-detect will work from there.');
      }

      const candidates = subnetCandidates(hostSeed);
      if (!candidates.length) {
        throw new Error('Could not build LAN scan candidates from the current network.');
      }

      const batchSize = 18;
      let found = null;
      for (let i = 0; i < candidates.length && !found; i += batchSize) {
        const batch = candidates.slice(i, i + batchSize);
        const results = await Promise.all(
          batch.map(async (host) => {
            const url = `http://${host}:8080/api/mobile/discover`;
            try {
              const data = await fetchJsonWithTimeout(url, { method: 'GET' }, 800);
              if (data?.ok && data?.service === 'ninoclaw') {
                return { host, data };
              }
            } catch (_scanError) {
            }
            return null;
          })
        );
        found = results.find(Boolean) || null;
      }

      if (!found) {
        throw new Error('No Ninoclaw dashboard found on this LAN subnet.');
      }

      const discoveredBaseUrl = `http://${found.host}:${found.data.port || 8080}`;
      setBaseUrl(discoveredBaseUrl);
      showSuccess(`Found ${found.data.agent_name || 'Ninoclaw'} at ${discoveredBaseUrl}`);
    } catch (scanError) {
      setError(scanError.message || 'Failed to auto-detect dashboard.');
    } finally {
      setDetectingDashboard(false);
    }
  }

  async function onRefresh() {
    setRefreshing(true);
    await loadAll(false);
  }

  async function sendMessage(text, replyTo = null) {
    const msgText = (typeof text === 'string' ? text : draft).trim();
    if (!msgText) return;
    setSending(true);
    setError('');
    const now = new Date().toISOString();
    const optimistic = { role: 'user', content: msgText, ts: now, type: 'text', status: 'sent', replyTo: replyTo || null };
    setChatMessages((current) => [...current, optimistic]);
    setDraft('');
    try {
      const response = await fetch(
        `${normalizeBaseUrl(baseUrl)}/api/chat/${encodeURIComponent(userId.trim())}/send`,
        { method: 'POST', headers, body: JSON.stringify({ message: msgText }) }
      );
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || `Send failed: ${response.status}`);
      setChatMessages((current) => [
        ...current,
        { role: 'assistant', content: data.reply, ts: new Date().toISOString(), type: 'text', status: 'delivered' },
      ]);
    } catch (sendError) {
      setError(sendError.message || 'Failed to send message.');
    } finally {
      setSending(false);
    }
  }

  async function sendMedia(media) {
    // media: { type, uri, base64?, fileName?, fileSize?, duration?, replyTo? }
    const now = new Date().toISOString();
    const optimistic = {
      role: 'user',
      type: media.type,
      uri: media.uri,
      fileName: media.fileName,
      fileSize: media.fileSize,
      duration: media.duration,
      content: media.type === 'image' ? '[Photo]' : media.type === 'file' ? `[File: ${media.fileName}]` : '[Voice message]',
      ts: now,
      status: 'sent',
      replyTo: media.replyTo || null,
    };
    setChatMessages((current) => [...current, optimistic]);

    setSending(true);
    try {
      const body = { message: media.content || '' };
      if (media.type === 'image' && media.base64) body.image_b64 = media.base64;
      if (media.type === 'file') body.message = body.message || `I sent you a file: ${media.fileName}`;
      if (media.type === 'audio') body.message = body.message || 'I sent you a voice message.';
      const response = await fetch(
        `${normalizeBaseUrl(baseUrl)}/api/chat/${encodeURIComponent(userId.trim())}/send`,
        { method: 'POST', headers, body: JSON.stringify(body) }
      );
      const data = await response.json();
      if (response.ok) {
        setChatMessages((current) => [
          ...current,
          { role: 'assistant', content: data.reply, ts: new Date().toISOString(), type: 'text', status: 'delivered' },
        ]);
      }
    } catch (_e) {
    } finally {
      setSending(false);
    }
  }

  async function handleExpoAction(name, action) {
    setActionBusy(`${action}:${name}`);
    setError('');
    try {
      await apiPost(`/api/mobile/mobile-apps/${encodeURIComponent(name)}/${action}`);
      await loadAll(false);
    } catch (actionError) {
      setError(actionError.message || `Failed to ${action} app.`);
    } finally {
      setActionBusy('');
    }
  }

  async function handleCreateReminder() {
    if (!reminderName.trim() || !reminderWhen.trim()) {
      setError('Reminder name and schedule are required.');
      return;
    }
    setActionBusy('create-reminder');
    setError('');
    setSuccess('');
    try {
      const result = editingTaskId
        ? await apiPost(`/api/mobile/tasks/reminders/${encodeURIComponent(editingTaskId)}`, {
            name: reminderName.trim(),
            when: reminderWhen.trim(),
          })
        : await apiPost('/api/mobile/tasks/reminders', {
            user_id: userId.trim(),
            name: reminderName.trim(),
            when: reminderWhen.trim(),
          });
      setTaskData(result.tasks || null);
      setReminderName('');
      setReminderWhen('');
      setEditingTaskId('');
      showSuccess(editingTaskId ? 'Reminder updated.' : 'Reminder created.');
      await loadAll(false);
    } catch (actionError) {
      setError(actionError.message || 'Failed to create reminder.');
    } finally {
      setActionBusy('');
    }
  }

  async function handleCreateCron() {
    if (!cronName.trim() || !cronExpression.trim() || !cronCommand.trim()) {
      setError('Cron name, schedule, and command are required.');
      return;
    }
    setActionBusy('create-cron');
    setError('');
    setSuccess('');
    try {
      const result = editingCronId
        ? await apiPost(`/api/mobile/tasks/crons/${encodeURIComponent(editingCronId)}`, {
            user_id: userId.trim(),
            name: cronName.trim(),
            expression: cronExpression.trim(),
            command: cronCommand.trim(),
          })
        : await apiPost('/api/mobile/tasks/crons', {
            user_id: userId.trim(),
            name: cronName.trim(),
            expression: cronExpression.trim(),
            command: cronCommand.trim(),
          });
      setTaskData(result.tasks || null);
      setCronName('');
      setCronExpression('');
      setCronCommand('');
      setEditingCronId('');
      showSuccess(editingCronId ? 'Recurring task updated.' : 'Recurring task created.');
      await loadAll(false);
    } catch (actionError) {
      setError(actionError.message || 'Failed to create recurring task.');
    } finally {
      setActionBusy('');
    }
  }

  async function handleCompleteTask(taskId) {
    setActionBusy(`done-task:${taskId}`);
    setError('');
    try {
      const result = await apiPost(`/api/mobile/tasks/reminders/${encodeURIComponent(taskId)}/complete`);
      setTaskData(result.tasks || null);
      showSuccess('Reminder completed.');
      await loadAll(false);
    } catch (actionError) {
      setError(actionError.message || 'Failed to complete reminder.');
    } finally {
      setActionBusy('');
    }
  }

  async function handleDeleteTask(taskId) {
    setActionBusy(`delete-task:${taskId}`);
    setError('');
    try {
      const result = await apiPost(`/api/mobile/tasks/reminders/${encodeURIComponent(taskId)}/delete`);
      setTaskData(result.tasks || null);
      if (editingTaskId === taskId) {
        setEditingTaskId('');
        setReminderName('');
        setReminderWhen('');
      }
      showSuccess('Reminder deleted.');
      await loadAll(false);
    } catch (actionError) {
      setError(actionError.message || 'Failed to delete reminder.');
    } finally {
      setActionBusy('');
    }
  }

  async function handleToggleCron(jobId, jobUserId) {
    setActionBusy(`toggle-cron:${jobId}`);
    setError('');
    try {
      const result = await apiPost(`/api/mobile/tasks/crons/${encodeURIComponent(jobId)}/toggle`, {
        user_id: String(jobUserId),
      });
      setTaskData(result.tasks || null);
      showSuccess('Recurring task updated.');
      await loadAll(false);
    } catch (actionError) {
      setError(actionError.message || 'Failed to update recurring task.');
    } finally {
      setActionBusy('');
    }
  }

  async function handleDeleteCron(jobId, jobUserId) {
    setActionBusy(`delete-cron:${jobId}`);
    setError('');
    try {
      const result = await apiPost(`/api/mobile/tasks/crons/${encodeURIComponent(jobId)}/delete`, {
        user_id: String(jobUserId),
      });
      setTaskData(result.tasks || null);
      if (editingCronId === jobId) {
        setEditingCronId('');
        setCronName('');
        setCronExpression('');
        setCronCommand('');
      }
      showSuccess('Recurring task deleted.');
      await loadAll(false);
    } catch (actionError) {
      setError(actionError.message || 'Failed to delete recurring task.');
    } finally {
      setActionBusy('');
    }
  }

  function beginEditTask(task) {
    setEditingTaskId(task.id);
    setReminderName(task.name || '');
    setReminderWhen('in 20 minutes');
    setSuccess('');
    setError('');
  }

  function beginEditCron(job) {
    setEditingCronId(job.id);
    setCronName(job.name || '');
    setCronExpression(job.original_expression || job.cron_expression || '');
    setCronCommand(job.command || '');
    setSuccess('');
    setError('');
  }

  function confirmDeleteTask(taskId) {
    Alert.alert('Delete reminder?', 'This reminder will be removed from Ninoclaw.', [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Delete', style: 'destructive', onPress: () => handleDeleteTask(taskId) },
    ]);
  }

  function confirmDeleteCron(jobId, jobUserId) {
    Alert.alert('Delete recurring task?', 'This schedule will be removed from Ninoclaw.', [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Delete', style: 'destructive', onPress: () => handleDeleteCron(jobId, jobUserId) },
    ]);
  }

  async function handleSaveModels() {
    setActionBusy('save-models');
    setError('');
    try {
      const result = await apiPost('/api/mobile/runtime/models', {
        primary: modelPrimary.trim(),
        fast: modelFast.trim(),
        smart: modelSmart.trim(),
      });
      setSettingsData(result.settings || null);
      await loadAll(false);
    } catch (actionError) {
      setError(actionError.message || 'Failed to save model settings.');
    } finally {
      setActionBusy('');
    }
  }

  async function handleTogglePlugin(key, enabled) {
    setActionBusy(`plugin:${key}`);
    setError('');
    try {
      const result = await apiPost(`/api/mobile/runtime/plugins/${encodeURIComponent(key)}`, { enabled });
      setSettingsData(result.settings || null);
      await loadAll(false);
    } catch (actionError) {
      setError(actionError.message || 'Failed to update plugin.');
    } finally {
      setActionBusy('');
    }
  }

  async function handleToggleMobileControl(enabled) {
    setActionBusy('mobile-control');
    setError('');
    try {
      const result = await apiPost('/api/mobile/runtime/mobile-control', { enabled });
      setSettingsData(result.settings || null);
      await loadAll(false);
    } catch (actionError) {
      setError(actionError.message || 'Failed to update mobile control setting.');
    } finally {
      setActionBusy('');
    }
  }

  async function handleRefreshAndroidAgent() {
    setActionBusy('refresh-android-agent');
    setError('');
    try {
      const status = await refreshAndroidAgentStatus();
      await registerMobileDevice(status);
      showSuccess(status?.available ? 'Android agent status refreshed.' : 'Android agent checked. Native module is not loaded in this build.');
    } catch (actionError) {
      setError(actionError.message || 'Failed to refresh Android agent status.');
    } finally {
      setActionBusy('');
    }
  }

  async function handleOpenAccessibilitySettings() {
    setActionBusy('open-accessibility-settings');
    setError('');
    try {
      const result = await openAndroidAccessibilitySettings();
      showSuccess(result?.summary || 'Opened accessibility settings.');
    } catch (actionError) {
      setError(actionError.message || 'Failed to open accessibility settings.');
    } finally {
      setActionBusy('');
    }
  }

  async function completeExecutorTask(taskId, status, result = {}, error = '') {
    if (!deviceId) {
      return;
    }
    try {
      await apiPost(`/api/mobile/device/${encodeURIComponent(deviceId)}/tasks/${taskId}/complete`, {
        status,
        result,
        error,
      });
    } catch (_completeError) {
    }
  }

  async function runAndroidAgentTask(task, nativeAction, successFallback) {
    const result = await performAndroidAgentAction(nativeAction, task?.payload || {});
    if (result?.status) {
      setAndroidAgentStatus(result.status);
    }
    if (result?.ok) {
      await completeExecutorTask(task.id, 'completed', result);
      return { ok: true, summary: result.summary || successFallback };
    }
    await completeExecutorTask(task.id, 'failed', result || {}, result?.summary || `Android agent action failed: ${nativeAction}`);
    return { ok: false, summary: result?.summary || `Android agent action failed: ${nativeAction}` };
  }

  async function executeExecutorTask(task) {
    const action = task?.action;
    const payload = task?.payload || {};
    if (action === 'ping') {
      await completeExecutorTask(task.id, 'completed', { pong: true, at: new Date().toISOString() });
      return { ok: true, summary: 'Ping acknowledged.' };
    }
    if (action === 'show_alert') {
      const title = payload.title || 'Ninoclaw';
      const message = payload.message || 'Dashboard requested your attention.';
      Alert.alert(title, message);
      await completeExecutorTask(task.id, 'completed', { shown: true, title, message });
      return { ok: true, summary: `Alert shown: ${title}` };
    }
    if (action === 'open_url') {
      const url = payload.url || payload.href || '';
      if (!url) {
        await completeExecutorTask(task.id, 'failed', {}, 'No url provided');
        return { ok: false, summary: 'open_url failed: no url provided' };
      }
      try {
        await Linking.openURL(url);
        await completeExecutorTask(task.id, 'completed', { opened: url });
        return { ok: true, summary: `Opened URL: ${url}` };
      } catch (openError) {
        await completeExecutorTask(task.id, 'failed', {}, openError.message || 'Could not open URL');
        return { ok: false, summary: `open_url failed: ${openError.message || 'unknown error'}` };
      }
    }
    if (action === 'open_settings') {
      try {
        await Linking.openSettings();
        await completeExecutorTask(task.id, 'completed', { opened: 'settings' });
        return { ok: true, summary: 'Opened device settings.' };
      } catch (settingsError) {
        await completeExecutorTask(task.id, 'failed', {}, settingsError.message || 'Could not open settings');
        return { ok: false, summary: `open_settings failed: ${settingsError.message || 'unknown error'}` };
      }
    }
    if (action === 'dial_number') {
      const phone = String(payload.phone || payload.number || '').trim();
      if (!phone) {
        await completeExecutorTask(task.id, 'failed', {}, 'No phone number provided');
        return { ok: false, summary: 'dial_number failed: no phone number provided' };
      }
      const url = `tel:${phone}`;
      try {
        await Linking.openURL(url);
        await completeExecutorTask(task.id, 'completed', { dialed: phone });
        return { ok: true, summary: `Opened dialer for ${phone}` };
      } catch (dialError) {
        await completeExecutorTask(task.id, 'failed', {}, dialError.message || 'Could not open dialer');
        return { ok: false, summary: `dial_number failed: ${dialError.message || 'unknown error'}` };
      }
    }
    if (action === 'send_sms') {
      const phone = String(payload.phone || payload.number || '').trim();
      const message = String(payload.message || '').trim();
      if (!phone) {
        await completeExecutorTask(task.id, 'failed', {}, 'No phone number provided');
        return { ok: false, summary: 'send_sms failed: no phone number provided' };
      }
      const url = `sms:${phone}${message ? `?body=${encodeURIComponent(message)}` : ''}`;
      try {
        await Linking.openURL(url);
        await completeExecutorTask(task.id, 'completed', { sms_to: phone, body: message });
        return { ok: true, summary: `Opened SMS composer for ${phone}` };
      } catch (smsError) {
        await completeExecutorTask(task.id, 'failed', {}, smsError.message || 'Could not open SMS composer');
        return { ok: false, summary: `send_sms failed: ${smsError.message || 'unknown error'}` };
      }
    }
    if (action === 'open_maps') {
      const query = String(payload.query || payload.destination || payload.place || '').trim();
      const lat = String(payload.lat || payload.latitude || '').trim();
      const lng = String(payload.lng || payload.longitude || '').trim();
      const url = query
        ? `geo:0,0?q=${encodeURIComponent(query)}`
        : lat && lng
          ? `geo:${lat},${lng}`
          : '';
      if (!url) {
        await completeExecutorTask(task.id, 'failed', {}, 'No map query or coordinates provided');
        return { ok: false, summary: 'open_maps failed: no query or coordinates provided' };
      }
      try {
        await Linking.openURL(url);
        await completeExecutorTask(task.id, 'completed', { opened: query || `${lat},${lng}` });
        return { ok: true, summary: `Opened maps for ${query || `${lat},${lng}`}` };
      } catch (mapsError) {
        await completeExecutorTask(task.id, 'failed', {}, mapsError.message || 'Could not open maps');
        return { ok: false, summary: `open_maps failed: ${mapsError.message || 'unknown error'}` };
      }
    }
    if (action === 'open_app') {
      const requested = String(payload.app || payload.name || '').trim();
      const candidates = appLaunchCandidates(requested, payload);
      if (!requested && !candidates.length) {
        await completeExecutorTask(task.id, 'failed', {}, 'No app or deep link provided');
        return { ok: false, summary: 'open_app failed: no app or deep link provided' };
      }
      let opened = '';
      let lastError = '';
      for (const candidate of candidates) {
        try {
          const supported = await Linking.canOpenURL(candidate);
          if (!supported) {
            continue;
          }
          await Linking.openURL(candidate);
          opened = candidate;
          break;
        } catch (candidateError) {
          lastError = candidateError.message || 'Could not open candidate';
        }
      }
      if (opened) {
        await completeExecutorTask(task.id, 'completed', { app: requested, url: opened });
        return { ok: true, summary: `Opened ${requested || opened}` };
      }
      await completeExecutorTask(task.id, 'failed', {}, lastError || `No launch route available for ${requested || 'requested app'}`);
      return { ok: false, summary: `open_app failed: ${lastError || 'no launch route available'}` };
    }
    if (action === 'android_agent_status') {
      const status = await refreshAndroidAgentStatus();
      await completeExecutorTask(task.id, 'completed', status);
      return {
        ok: true,
        summary: status?.available
          ? (status?.serviceEnabled ? 'Android agent is available and service is enabled.' : 'Android agent is available, but accessibility service is still disabled.')
          : 'Android agent is not available in this build.',
      };
    }
    if (action === 'open_accessibility_settings') {
      try {
        const result = await openAndroidAccessibilitySettings();
        await completeExecutorTask(task.id, 'completed', result);
        return { ok: true, summary: result.summary || 'Opened accessibility settings.' };
      } catch (settingsError) {
        await completeExecutorTask(task.id, 'failed', {}, settingsError.message || 'Could not open accessibility settings');
        return { ok: false, summary: settingsError.message || 'Could not open accessibility settings' };
      }
    }
    if (action === 'agent_press_back') {
      return runAndroidAgentTask(task, 'press_back', 'Pressed Back via Android agent.');
    }
    if (action === 'agent_open_notifications') {
      return runAndroidAgentTask(task, 'open_notifications', 'Opened notification shade via Android agent.');
    }
    if (action === 'agent_open_quick_settings') {
      return runAndroidAgentTask(task, 'open_quick_settings', 'Opened quick settings via Android agent.');
    }
    if (action === 'agent_read_screen') {
      return runAndroidAgentTask(task, 'read_screen', 'Collected Android screen snapshot.');
    }
    if (action === 'agent_tap') {
      return runAndroidAgentTask(task, 'tap', 'Requested Android tap action.');
    }
    if (action === 'agent_type_text') {
      return runAndroidAgentTask(task, 'type_text', 'Requested Android text input action.');
    }

    await completeExecutorTask(task.id, 'failed', {}, `Unsupported action: ${action}`);
    return { ok: false, summary: `Unsupported action: ${action}` };
  }

  async function pollExecutorTasks() {
    if (!deviceId || !normalizeBaseUrl(baseUrl) || !password.trim()) {
      return;
    }
    try {
      const result = await apiGet(`/api/mobile/device/${encodeURIComponent(deviceId)}/tasks`);
      const tasks = result?.tasks || [];
      setExecutorTasks(tasks);
      for (const task of tasks) {
        const summary = await executeExecutorTask(task);
        setExecutorLog((current) => [
          { id: `${task.id}-${Date.now()}`, text: summary.summary, at: new Date().toISOString() },
          ...current,
        ].slice(0, 12));
      }
      if (result?.mobile_control && settingsData) {
        setSettingsData((current) => ({ ...(current || {}), mobile_control: result.mobile_control }));
      }
    } catch (_pollError) {
    }
  }

  async function handleReloadRuntime() {
    setActionBusy('reload-runtime');
    setError('');
    try {
      const result = await apiPost('/api/mobile/runtime/reload');
      setSettingsData(result.settings || null);
      await loadAll(false);
    } catch (actionError) {
      setError(actionError.message || 'Failed to reload runtime.');
    } finally {
      setActionBusy('');
    }
  }

  async function handleFixEnv() {
    setActionBusy('fixenv');
    setError('');
    setSuccess('');
    try {
      const result = await apiPost('/api/mobile/runtime/fixenv');
      setRuntimeHealth(result.health || null);
      showSuccess(result.ok ? 'Environment repair finished.' : 'Environment repair completed with warnings.');
      await loadAll(false);
    } catch (actionError) {
      setError(actionError.message || 'Failed to run fix environment.');
    } finally {
      setActionBusy('');
    }
  }

  const content = (() => {
    if (!overview && !loading) {
      return (
        <ConnectionGate
          baseUrl={baseUrl}
          password={password}
          userId={userId}
          onChange={(field, value) => {
            if (field === 'baseUrl') setBaseUrl(value);
            if (field === 'password') setPassword(value);
            if (field === 'userId') setUserId(value);
          }}
          onReload={() => loadAll(true)}
          onAutoDetect={autoDetectDashboard}
          loading={loading}
          detecting={detectingDashboard}
          error={error}
          detectedUrl={inferDashboardUrl()}
          lastSyncedAt={lastSyncedAt}
        />
      );
    }

      switch (activeTab) {
      case 'tasks':
        return (
          <TasksTab
            taskData={taskData}
            reminderName={reminderName}
            setReminderName={setReminderName}
            reminderWhen={reminderWhen}
            setReminderWhen={setReminderWhen}
            cronName={cronName}
            setCronName={setCronName}
            cronExpression={cronExpression}
            setCronExpression={setCronExpression}
            cronCommand={cronCommand}
            setCronCommand={setCronCommand}
            onCreateReminder={handleCreateReminder}
            onCreateCron={handleCreateCron}
            onCompleteTask={handleCompleteTask}
            onDeleteTask={confirmDeleteTask}
            onToggleCron={handleToggleCron}
            onDeleteCron={confirmDeleteCron}
            onEditTask={beginEditTask}
            onEditCron={beginEditCron}
            editingTaskId={editingTaskId}
            editingCronId={editingCronId}
            onCancelTaskEdit={() => {
              setEditingTaskId('');
              setReminderName('');
              setReminderWhen('');
            }}
            onCancelCronEdit={() => {
              setEditingCronId('');
              setCronName('');
              setCronExpression('');
              setCronCommand('');
            }}
            actionBusy={actionBusy}
          />
        );
      case 'builds':
        return (
          <BuildsTab
            baseUrl={baseUrl}
            buildsData={buildsData}
            mobileAppsData={mobileAppsData}
            onExpoAction={handleExpoAction}
            actionBusy={actionBusy}
          />
        );
      case 'settings':
        return (
          <SettingsTab
            baseUrl={baseUrl}
            password={password}
            userId={userId}
            onChange={(field, value) => {
              if (field === 'baseUrl') setBaseUrl(value);
              if (field === 'password') setPassword(value);
              if (field === 'userId') setUserId(value);
            }}
            onReload={() => loadAll(true)}
            onAutoDetect={autoDetectDashboard}
            loading={loading}
            detecting={detectingDashboard}
            settingsData={settingsData}
            runtimeHealth={runtimeHealth}
            overview={overview}
            error={error}
            detectedUrl={inferDashboardUrl()}
            lastSyncedAt={lastSyncedAt}
            modelPrimary={modelPrimary}
            setModelPrimary={setModelPrimary}
            modelFast={modelFast}
            setModelFast={setModelFast}
            modelSmart={modelSmart}
            setModelSmart={setModelSmart}
            onSaveModels={handleSaveModels}
            onTogglePlugin={handleTogglePlugin}
            onToggleMobileControl={handleToggleMobileControl}
            androidAgentStatus={androidAgentStatus}
            onRefreshAndroidAgent={handleRefreshAndroidAgent}
            onOpenAccessibilitySettings={handleOpenAccessibilitySettings}
            onReloadRuntime={handleReloadRuntime}
            onFixEnv={handleFixEnv}
            actionBusy={actionBusy}
            executorTasks={executorTasks}
            executorLog={executorLog}
          />
        );
      case 'chat':
      default:
        return null;
    }
  })();

  useEffect(() => {
    let mounted = true;
    async function bootstrap() {
      try {
        const raw = await AsyncStorage.getItem(STORAGE_KEY);
        const savedDeviceId = await getOrCreateDeviceId();
        const nativeStatus = await getAndroidAgentStatus();
        if (mounted) {
          setDeviceId(savedDeviceId);
          setAndroidAgentStatus(nativeStatus);
        }
        if (raw && mounted) {
          const saved = JSON.parse(raw);
          if (saved.baseUrl) setBaseUrl(saved.baseUrl);
          if (saved.password) setPassword(saved.password);
          if (saved.userId) setUserId(saved.userId);
          if (!saved.baseUrl) {
            const inferred = inferDashboardUrl();
            if (inferred) setBaseUrl(inferred);
          }
          if (saved.baseUrl && saved.password && saved.userId) {
            setTimeout(() => {
              loadAll(true);
            }, 0);
          }
        } else {
          const inferred = inferDashboardUrl();
          if (inferred && mounted) {
            setBaseUrl(inferred);
          }
        }
      } catch (_error) {
      } finally {
        if (mounted) {
          setBootstrapped(true);
        }
      }
    }
    bootstrap();
    return () => {
      mounted = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!bootstrapped) {
      return;
    }
    AsyncStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        baseUrl,
        password,
        userId,
      })
    ).catch(() => {});
  }, [baseUrl, password, userId, bootstrapped]);

  useEffect(() => {
    if (!settingsData?.mobile_control?.enabled || !deviceId || !baseUrl || !password) {
      return undefined;
    }
    let cancelled = false;
    async function tick() {
      if (cancelled) {
        return;
      }
      await pollExecutorTasks();
    }
    tick();
    const id = setInterval(tick, 8000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [settingsData?.mobile_control?.enabled, deviceId, baseUrl, password]);

  // Chat tab gets its own full-screen layout (no ScrollView)
  if (activeTab === 'chat' && overview) {
    return (
      <SafeAreaView style={styles.safe}>
        <StatusBar barStyle="light-content" backgroundColor="#1a2332" />
        <ChatScreen
          chatMessages={chatMessages}
          draft={draft}
          setDraft={setDraft}
          onSend={sendMessage}
          onSendMedia={sendMedia}
          sending={sending}
          userId={userId.trim() || 'mobile'}
          overview={overview}
          activeTab={activeTab}
          setActiveTab={setActiveTab}
        />
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.safe}>
      <StatusBar barStyle="light-content" backgroundColor={COLORS.bg} />
      <View style={styles.screen}>
        <ScrollView
          style={styles.scroll}
          contentContainerStyle={styles.content}
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={COLORS.cyan} />
          }
        >
          <View style={styles.topbar}>
            <View style={styles.topbarLeft}>
              <Image source={MASCOT} style={styles.brandMascot} resizeMode="contain" />
              <View>
                <Text style={styles.brand}>Ninoclaw</Text>
                <Text style={styles.topline}>
                  {normalizeBaseUrl(baseUrl) ? normalizeBaseUrl(baseUrl) : 'Connect to your local dashboard'}
                </Text>
              </View>
            </View>
            <View style={[styles.pulseDot, overview ? styles.pulseLive : styles.pulseIdle]} />
          </View>

          {!!success && <Text style={styles.successText}>{success}</Text>}
          {!!error && overview && activeTab !== 'settings' && <Text style={styles.errorText}>{error}</Text>}

          {loading && !overview ? (
            <View style={styles.loaderWrap}>
              <ActivityIndicator size="large" color={COLORS.cyan} />
              <Text style={styles.loaderText}>Loading your live Ninoclaw data...</Text>
            </View>
          ) : (
            content
          )}
        </ScrollView>

        <View style={styles.bottomTabShell}>
          <View style={styles.bottomTabBar}>
            {TABS.map((tab) => {
              const isActive = tab.key === activeTab;
              return (
                <TouchableOpacity
                  key={tab.key}
                  onPress={() => setActiveTab(tab.key)}
                  style={styles.bottomTabButton}
                >
                  <Text style={[styles.bottomTabText, isActive && styles.bottomTabTextActive]}>
                    {tab.label}
                  </Text>
                  <View style={[styles.bottomTabIndicator, isActive && styles.bottomTabIndicatorActive]} />
                </TouchableOpacity>
              );
            })}
          </View>
        </View>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: COLORS.bg,
  },
  screen: {
    flex: 1,
    backgroundColor: COLORS.bg,
  },
  scroll: {
    flex: 1,
    backgroundColor: COLORS.bg,
  },
  content: {
    paddingHorizontal: 18,
    paddingTop: 10,
    paddingBottom: 130,
  },
  topbar: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 20,
  },
  topbarLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    flex: 1,
  },
  brandMascot: {
    width: 54,
    height: 54,
  },
  brand: {
    color: COLORS.text,
    fontSize: 28,
    fontWeight: '800',
    letterSpacing: 0.4,
  },
  topline: {
    color: COLORS.muted,
    marginTop: 4,
    fontSize: 14,
    maxWidth: 280,
  },
  pulseDot: {
    width: 12,
    height: 12,
    borderRadius: 999,
  },
  pulseLive: {
    backgroundColor: COLORS.green,
  },
  pulseIdle: {
    backgroundColor: COLORS.coral,
  },
  sectionHeader: {
    marginBottom: 16,
  },
  sectionEyebrow: {
    color: COLORS.cyan,
    fontSize: 12,
    fontWeight: '800',
    textTransform: 'uppercase',
    letterSpacing: 1.4,
    marginBottom: 8,
  },
  sectionTitle: {
    color: COLORS.text,
    fontSize: 25,
    lineHeight: 31,
    fontWeight: '800',
  },
  sectionBody: {
    color: COLORS.muted,
    fontSize: 15,
    lineHeight: 22,
    marginTop: 10,
  },
  heroCard: {
    backgroundColor: COLORS.panel,
    borderWidth: 1,
    borderColor: COLORS.line,
    borderRadius: 24,
    padding: 22,
    marginBottom: 16,
  },
  heroRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  heroCopy: {
    flex: 1,
  },
  heroLabel: {
    color: COLORS.cyan,
    fontWeight: '800',
    fontSize: 12,
    letterSpacing: 1.3,
    textTransform: 'uppercase',
    marginBottom: 10,
  },
  heroTitle: {
    color: COLORS.text,
    fontSize: 22,
    lineHeight: 28,
    fontWeight: '800',
    marginBottom: 10,
  },
  heroBody: {
    color: COLORS.muted,
    fontSize: 15,
    lineHeight: 22,
  },
  heroMascot: {
    width: 110,
    height: 110,
  },
  connectionHero: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    marginBottom: 6,
  },
  connectionMascot: {
    width: 84,
    height: 84,
  },
  connectionCopy: {
    flex: 1,
  },
  metricsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
    marginBottom: 18,
  },
  metricCard: {
    width: '48.2%',
    borderRadius: 20,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
  },
  metricCyan: {
    backgroundColor: '#0f2635',
    borderColor: '#204761',
  },
  metricAmber: {
    backgroundColor: '#302414',
    borderColor: '#594224',
  },
  metricGreen: {
    backgroundColor: '#102820',
    borderColor: '#24483b',
  },
  metricBlue: {
    backgroundColor: '#13253a',
    borderColor: '#264b74',
  },
  metricValue: {
    color: COLORS.text,
    fontSize: 26,
    fontWeight: '800',
    marginBottom: 6,
  },
  metricLabel: {
    color: COLORS.muted,
    fontSize: 13,
    lineHeight: 18,
  },
  panel: {
    backgroundColor: COLORS.panel,
    borderWidth: 1,
    borderColor: COLORS.line,
    borderRadius: 24,
    padding: 16,
    marginBottom: 16,
  },
  panelSoft: {
    backgroundColor: COLORS.panelSoft,
    borderWidth: 1,
    borderColor: COLORS.line,
    borderRadius: 22,
    padding: 18,
    marginBottom: 16,
  },
  settingsMascot: {
    width: 92,
    height: 92,
    alignSelf: 'flex-end',
    marginTop: 10,
  },
  panelTitle: {
    color: COLORS.text,
    fontSize: 17,
    fontWeight: '800',
    marginBottom: 12,
  },
  panelBody: {
    color: COLORS.muted,
    fontSize: 14,
    lineHeight: 21,
    marginBottom: 12,
  },
  helperText: {
    color: COLORS.muted,
    fontSize: 12,
    lineHeight: 18,
    marginBottom: 10,
  },
  bubble: {
    borderRadius: 18,
    padding: 14,
    marginBottom: 10,
  },
  userBubble: {
    backgroundColor: '#1a3558',
    alignSelf: 'flex-end',
  },
  assistantBubble: {
    backgroundColor: COLORS.card,
    alignSelf: 'stretch',
  },
  bubbleRole: {
    color: COLORS.cyan,
    fontSize: 11,
    fontWeight: '800',
    textTransform: 'uppercase',
    letterSpacing: 1,
    marginBottom: 6,
  },
  bubbleText: {
    color: COLORS.text,
    fontSize: 14,
    lineHeight: 21,
  },
  bubbleTime: {
    color: COLORS.muted,
    fontSize: 11,
    marginTop: 8,
  },
  composer: {
    backgroundColor: COLORS.panel,
    borderWidth: 1,
    borderColor: COLORS.line,
    borderRadius: 22,
    padding: 12,
    marginBottom: 10,
  },
  chatContainer: {
    flex: 1,
  },
  chatMessages: {
    paddingHorizontal: 12,
    paddingTop: 8,
    paddingBottom: 4,
  },
  chatRowUser: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    marginBottom: 8,
  },
  chatRowAssistant: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    marginBottom: 8,
    gap: 8,
  },
  chatAvatar: {
    width: 30,
    height: 30,
    borderRadius: 15,
    backgroundColor: COLORS.card,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 2,
    flexShrink: 0,
  },
  chatBubble: {
    maxWidth: '80%',
    borderRadius: 18,
    paddingHorizontal: 14,
    paddingVertical: 10,
  },
  chatBubbleUser: {
    backgroundColor: '#1d4ed8',
    borderBottomRightRadius: 4,
  },
  chatBubbleAssistant: {
    backgroundColor: COLORS.panelSoft,
    borderBottomLeftRadius: 4,
  },
  chatBubbleText: {
    color: COLORS.text,
    fontSize: 15,
    lineHeight: 22,
  },
  chatBubbleTime: {
    color: 'rgba(255,255,255,0.4)',
    fontSize: 10,
    marginTop: 4,
    textAlign: 'right',
  },
  chatEmpty: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 60,
  },
  chatComposer: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    paddingHorizontal: 12,
    paddingVertical: 10,
    borderTopWidth: 1,
    borderTopColor: COLORS.line,
    backgroundColor: COLORS.bg,
    gap: 8,
  },
  chatInput: {
    flex: 1,
    color: COLORS.text,
    backgroundColor: COLORS.panelSoft,
    borderRadius: 22,
    paddingHorizontal: 16,
    paddingVertical: 10,
    fontSize: 15,
    maxHeight: 120,
  },
  chatSendBtn: {
    width: 42,
    height: 42,
    borderRadius: 21,
    backgroundColor: '#1d4ed8',
    alignItems: 'center',
    justifyContent: 'center',
  },
  chatSendBtnText: {
    color: COLORS.text,
    fontSize: 20,
    fontWeight: '700',
    lineHeight: 24,
  },
  input: {
    color: COLORS.text,
    backgroundColor: COLORS.panelSoft,
    borderRadius: 16,
    paddingHorizontal: 14,
    paddingVertical: 14,
    fontSize: 15,
    marginBottom: 10,
  },
  primaryButton: {
    backgroundColor: COLORS.text,
    borderRadius: 16,
    paddingVertical: 14,
    alignItems: 'center',
  },
  primaryButtonText: {
    color: COLORS.bg,
    fontSize: 14,
    fontWeight: '800',
  },
  ghostButton: {
    marginTop: 10,
    alignItems: 'center',
    paddingVertical: 10,
  },
  ghostButtonText: {
    color: COLORS.muted,
    fontSize: 13,
    fontWeight: '700',
  },
  rowCard: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 14,
    borderBottomWidth: 1,
    borderBottomColor: COLORS.line,
  },
  rowMain: {
    flex: 1,
    paddingRight: 12,
  },
  rowTitle: {
    color: COLORS.text,
    fontSize: 15,
    fontWeight: '700',
    marginBottom: 6,
  },
  rowMeta: {
    color: COLORS.muted,
    fontSize: 13,
  },
  rowSubtle: {
    color: COLORS.muted,
    fontSize: 12,
    lineHeight: 18,
    marginTop: 6,
  },
  rowActions: {
    alignItems: 'flex-end',
    gap: 8,
  },
  badge: {
    backgroundColor: '#123528',
    borderWidth: 1,
    borderColor: '#2e7158',
    borderRadius: 999,
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  badgeMuted: {
    backgroundColor: '#262f3d',
    borderColor: '#455163',
  },
  badgeText: {
    color: COLORS.text,
    fontSize: 12,
    fontWeight: '800',
  },
  buildCard: {
    paddingVertical: 14,
    borderBottomWidth: 1,
    borderBottomColor: COLORS.line,
  },
  buildTop: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: 12,
    marginBottom: 6,
  },
  buildName: {
    color: COLORS.text,
    fontSize: 16,
    fontWeight: '800',
    flex: 1,
  },
  buildStatus: {
    color: COLORS.cyan,
    fontSize: 12,
    fontWeight: '800',
  },
  buildType: {
    color: COLORS.amber,
    fontSize: 13,
    fontWeight: '700',
    marginBottom: 6,
  },
  buildDetail: {
    color: COLORS.muted,
    fontSize: 14,
    lineHeight: 20,
    marginBottom: 12,
  },
  buildActions: {
    flexDirection: 'row',
    gap: 10,
  },
  secondaryButton: {
    backgroundColor: COLORS.panelSoft,
    borderWidth: 1,
    borderColor: COLORS.line,
    borderRadius: 14,
    paddingHorizontal: 14,
    paddingVertical: 10,
  },
  secondaryButtonText: {
    color: COLORS.text,
    fontSize: 13,
    fontWeight: '700',
  },
  buttonDisabled: {
    opacity: 0.6,
  },
  settingRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 14,
    borderBottomWidth: 1,
    borderBottomColor: COLORS.line,
    gap: 12,
  },
  settingTitle: {
    color: COLORS.text,
    fontSize: 14,
    fontWeight: '700',
    flex: 1,
  },
  settingValue: {
    color: COLORS.muted,
    fontSize: 13,
    flexShrink: 1,
    textAlign: 'right',
  },
  emptyState: {
    paddingVertical: 20,
  },
  emptyTitle: {
    color: COLORS.text,
    fontSize: 15,
    fontWeight: '700',
    marginBottom: 6,
  },
  emptyBody: {
    color: COLORS.muted,
    fontSize: 14,
    lineHeight: 20,
  },
  bottomTabShell: {
    position: 'absolute',
    left: 0,
    right: 0,
    bottom: 0,
    paddingHorizontal: 16,
    paddingTop: 10,
    paddingBottom: 48,
    backgroundColor: 'rgba(7, 17, 31, 0.92)',
  },
  bottomTabBar: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    backgroundColor: COLORS.panel,
    borderWidth: 1,
    borderColor: COLORS.line,
    borderRadius: 24,
    paddingHorizontal: 8,
    paddingVertical: 8,
  },
  bottomTabButton: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 10,
    gap: 6,
  },
  bottomTabText: {
    color: COLORS.muted,
    fontSize: 12,
    fontWeight: '700',
  },
  bottomTabTextActive: {
    color: COLORS.text,
  },
  bottomTabIndicator: {
    width: 18,
    height: 4,
    borderRadius: 999,
    backgroundColor: 'transparent',
  },
  bottomTabIndicatorActive: {
    backgroundColor: COLORS.cyan,
  },
  loaderWrap: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 80,
  },
  loaderText: {
    color: COLORS.muted,
    marginTop: 14,
    fontSize: 14,
  },
  errorText: {
    color: COLORS.coral,
    marginBottom: 12,
    fontSize: 13,
    lineHeight: 18,
  },
  successText: {
    color: COLORS.green,
    marginBottom: 12,
    fontSize: 13,
    lineHeight: 18,
  },
});

// ─── Telegram-style stylesheet ───────────────────────────────────────────────
const tgStyles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: '#0d1520',
  },
  // Header
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#1a2332',
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: '#243248',
    gap: 12,
  },
  headerAvatar: {
    width: 42,
    height: 42,
    borderRadius: 21,
    backgroundColor: '#243248',
  },
  headerName: {
    color: '#edf4ff',
    fontSize: 17,
    fontWeight: '700',
  },
  headerSub: {
    color: '#97a8c4',
    fontSize: 13,
  },
  onlineDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: '#97a8c4',
  },
  // Messages
  messageList: {
    paddingHorizontal: 8,
    paddingTop: 8,
    paddingBottom: 12,
  },
  msgRow: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    marginBottom: 2,
    paddingHorizontal: 4,
  },
  msgRowUser: {
    justifyContent: 'flex-end',
  },
  msgRowAssistant: {
    justifyContent: 'flex-start',
    gap: 6,
  },
  avatarCircle: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: '#1a3558',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 2,
    flexShrink: 0,
  },
  bubble: {
    maxWidth: '78%',
    paddingHorizontal: 12,
    paddingTop: 8,
    paddingBottom: 6,
    borderRadius: 18,
  },
  bubbleUser: {
    backgroundColor: '#1d4ca3',
    borderBottomRightRadius: 4,
  },
  bubbleAssistant: {
    backgroundColor: '#1e2d40',
    borderBottomLeftRadius: 4,
  },
  msgText: {
    color: '#edf4ff',
    fontSize: 15,
    lineHeight: 22,
  },
  msgMetaRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'flex-end',
    marginTop: 4,
    gap: 2,
  },
  msgMeta: {
    color: 'rgba(237,244,255,0.45)',
    fontSize: 11,
  },
  msgStatus: {
    color: '#4fc3f7',
    fontSize: 12,
  },
  // Day separator
  dayPill: {
    alignItems: 'center',
    marginVertical: 12,
  },
  dayPillText: {
    backgroundColor: 'rgba(26,35,50,0.85)',
    color: '#97a8c4',
    fontSize: 12,
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 12,
    overflow: 'hidden',
  },
  // Reply preview inside bubble
  msgReplyPreview: {
    flexDirection: 'row',
    backgroundColor: 'rgba(255,255,255,0.07)',
    borderRadius: 8,
    marginBottom: 2,
    paddingVertical: 4,
    paddingHorizontal: 8,
    maxWidth: '78%',
    gap: 6,
  },
  msgReplyAccent: {
    width: 3,
    borderRadius: 2,
    backgroundColor: '#4fc3f7',
  },
  msgReplyFrom: {
    color: '#4fc3f7',
    fontSize: 12,
    fontWeight: '700',
    marginBottom: 1,
  },
  msgReplyText: {
    color: '#97a8c4',
    fontSize: 12,
  },
  // Image message
  msgImage: {
    width: 220,
    height: 160,
    borderRadius: 10,
    marginBottom: 4,
  },
  // File message
  fileRow: {
    flexDirection: 'row',
    alignItems: 'center',
    minWidth: 180,
  },
  fileName: {
    color: '#edf4ff',
    fontSize: 14,
    fontWeight: '600',
  },
  fileSize: {
    color: '#97a8c4',
    fontSize: 12,
    marginTop: 2,
  },
  // Audio message
  audioRow: {
    flexDirection: 'row',
    alignItems: 'center',
    minWidth: 160,
  },
  audioBar: {
    flex: 1,
    height: 24,
    backgroundColor: 'rgba(255,255,255,0.1)',
    borderRadius: 12,
    overflow: 'hidden',
    justifyContent: 'center',
    paddingHorizontal: 6,
  },
  audioWave: {
    height: 3,
    backgroundColor: '#4fc3f7',
    borderRadius: 2,
    width: '60%',
  },
  // Empty state
  emptyChat: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingTop: 80,
    paddingHorizontal: 32,
  },
  emptyChatText: {
    color: '#97a8c4',
    fontSize: 15,
    textAlign: 'center',
    lineHeight: 22,
  },
  // Reply bar above composer
  replyBar: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#1a2332',
    borderTopWidth: 1,
    borderTopColor: '#243248',
    paddingHorizontal: 12,
    paddingVertical: 8,
    gap: 8,
  },
  replyBarAccent: {
    width: 3,
    height: '100%',
    minHeight: 32,
    borderRadius: 2,
    backgroundColor: '#4fc3f7',
  },
  replyBarFrom: {
    color: '#4fc3f7',
    fontSize: 12,
    fontWeight: '700',
    marginBottom: 1,
  },
  replyBarText: {
    color: '#97a8c4',
    fontSize: 13,
  },
  replyBarClose: {
    padding: 4,
  },
  // Attach menu
  attachMenu: {
    backgroundColor: '#1a2332',
    borderTopWidth: 1,
    borderTopColor: '#243248',
    flexDirection: 'row',
    justifyContent: 'space-around',
    paddingVertical: 16,
    paddingHorizontal: 24,
  },
  attachOption: {
    alignItems: 'center',
    gap: 8,
  },
  attachIconWrap: {
    width: 54,
    height: 54,
    borderRadius: 27,
    backgroundColor: '#243248',
    alignItems: 'center',
    justifyContent: 'center',
  },
  attachLabel: {
    color: '#97a8c4',
    fontSize: 12,
  },
  // Emoji picker
  emojiPicker: {
    backgroundColor: '#1a2332',
    borderTopWidth: 1,
    borderTopColor: '#243248',
    paddingVertical: 10,
  },
  emojiBtn: {
    paddingHorizontal: 8,
    paddingVertical: 4,
  },
  // Composer
  composer: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    backgroundColor: '#1a2332',
    borderTopWidth: 1,
    borderTopColor: '#243248',
    paddingHorizontal: 8,
    paddingVertical: 8,
    gap: 6,
  },
  composerBtn: {
    width: 38,
    height: 38,
    alignItems: 'center',
    justifyContent: 'center',
  },
  composerInput: {
    flex: 1,
    color: '#edf4ff',
    backgroundColor: '#243248',
    borderRadius: 20,
    paddingHorizontal: 14,
    paddingVertical: 9,
    fontSize: 15,
    maxHeight: 120,
  },
  sendBtn: {
    width: 38,
    height: 38,
    borderRadius: 19,
    backgroundColor: '#1d4ca3',
    alignItems: 'center',
    justifyContent: 'center',
  },
  sendBtnIcon: {
    color: '#edf4ff',
    fontSize: 16,
    fontWeight: '700',
  },
  // Voice button
  voiceBtn: {
    width: 38,
    height: 38,
    borderRadius: 19,
    backgroundColor: '#243248',
    alignItems: 'center',
    justifyContent: 'center',
  },
  voiceBtnActive: {
    backgroundColor: '#c0392b',
  },
  // Pending media preview bar
  pendingBar: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#1a2e44',
    borderTopWidth: 1,
    borderTopColor: '#243248',
    paddingHorizontal: 12,
    paddingVertical: 8,
    gap: 10,
  },
  pendingThumb: {
    width: 48,
    height: 48,
    borderRadius: 8,
    backgroundColor: '#243248',
  },
  pendingFileIcon: {
    width: 48,
    height: 48,
    borderRadius: 8,
    backgroundColor: '#243248',
    alignItems: 'center',
    justifyContent: 'center',
  },
  pendingLabel: {
    color: '#edf4ff',
    fontSize: 13,
    fontWeight: '600',
  },
  pendingHint: {
    color: '#97a8c4',
    fontSize: 11,
    marginTop: 2,
  },
  // Context menu
  ctxOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
  },
  ctxMenu: {
    position: 'absolute',
    backgroundColor: '#1e2d40',
    borderRadius: 12,
    minWidth: 160,
    shadowColor: '#000',
    shadowOpacity: 0.4,
    shadowRadius: 8,
    elevation: 8,
  },
  ctxItem: {
    paddingHorizontal: 18,
    paddingVertical: 13,
    borderBottomWidth: 1,
    borderBottomColor: '#243248',
  },
  ctxItemText: {
    color: '#edf4ff',
    fontSize: 15,
  },
  // Tab bar inside ChatScreen
  tabBar: {
    flexDirection: 'row',
    backgroundColor: '#1a2332',
    borderTopWidth: 1,
    borderTopColor: '#243248',
    paddingBottom: 28,
  },
  tabBtn: {
    flex: 1,
    alignItems: 'center',
    paddingVertical: 10,
    gap: 4,
  },
  tabText: {
    color: '#97a8c4',
    fontSize: 13,
    fontWeight: '600',
  },
  tabTextActive: {
    color: '#4fc3f7',
  },
  tabIndicator: {
    height: 2,
    width: 24,
    borderRadius: 1,
    backgroundColor: 'transparent',
  },
  tabIndicatorActive: {
    backgroundColor: '#4fc3f7',
  },
});
