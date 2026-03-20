import React, { useEffect, useMemo, useState } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import {
  ActivityIndicator,
  Image,
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
const MASCOT = require('./assets/mascot.png');

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

function ConnectionGate({ baseUrl, password, userId, onChange, onReload, loading, error }) {
  return (
    <View style={styles.panel}>
      <View style={styles.connectionHero}>
        <Image source={MASCOT} style={styles.connectionMascot} resizeMode="contain" />
        <View style={styles.connectionCopy}>
          <Text style={styles.panelTitle}>Connect to your dashboard</Text>
          <Text style={styles.panelBody}>
            Enter your Ninoclaw dashboard LAN URL, dashboard password, and a mobile chat user id.
          </Text>
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

      <TouchableOpacity style={styles.primaryButton} onPress={onReload} disabled={loading}>
        <Text style={styles.primaryButtonText}>{loading ? 'Connecting...' : 'Load live data'}</Text>
      </TouchableOpacity>
    </View>
  );
}

function ChatTab({ overview, chatMessages, draft, setDraft, onSend, sending, userId }) {
  const stats = [
    { label: 'Runs Today', value: overview?.stats?.total_messages ?? '0', tone: 'cyan' },
    { label: 'Pending Tasks', value: overview?.stats?.pending_tasks ?? '0', tone: 'amber' },
    { label: 'Live Builds', value: overview?.stats?.total_builds ?? '0', tone: 'green' },
    { label: 'Expo Apps', value: overview?.stats?.expo_apps ?? '0', tone: 'blue' },
  ];

  return (
    <View>
      <SectionTitle
        eyebrow="Companion"
        title="Live agent chat"
        body={`Connected to user id "${userId}" through your real Ninoclaw dashboard APIs.`}
      />

      <View style={styles.heroCard}>
        <View style={styles.heroRow}>
          <View style={styles.heroCopy}>
            <Text style={styles.heroLabel}>Ninoclaw</Text>
            <Text style={styles.heroTitle}>Desktop control room, compressed into a mobile command surface.</Text>
            <Text style={styles.heroBody}>
              The cards below are now pulled from your live dashboard, and the composer sends real messages to the agent loop.
            </Text>
          </View>
          <Image source={MASCOT} style={styles.heroMascot} resizeMode="contain" />
        </View>
      </View>

      <View style={styles.metricsGrid}>
        {stats.map((item) => (
          <MetricCard key={item.label} label={item.label} value={String(item.value)} tone={item.tone} />
        ))}
      </View>

      <View style={styles.panel}>
        <Text style={styles.panelTitle}>Conversation</Text>
        {chatMessages.length ? (
          chatMessages.map((message, index) => (
            <View
              key={`${message.role}-${index}-${message.ts || ''}`}
              style={[
                styles.bubble,
                message.role === 'user' ? styles.userBubble : styles.assistantBubble,
              ]}
            >
              <Text style={styles.bubbleRole}>{message.role === 'user' ? 'You' : 'Ninoclaw'}</Text>
              <Text style={styles.bubbleText}>{message.content}</Text>
              {!!message.ts && <Text style={styles.bubbleTime}>{formatTimestamp(message.ts)}</Text>}
            </View>
          ))
        ) : (
          <EmptyState title="No messages yet" body="Send a message below to start a live conversation." />
        )}
      </View>

      <View style={styles.composer}>
        <TextInput
          value={draft}
          onChangeText={setDraft}
          placeholder="Message Ninoclaw..."
          placeholderTextColor={COLORS.muted}
          style={styles.input}
          multiline
        />
        <TouchableOpacity style={styles.primaryButton} onPress={onSend} disabled={sending || !draft.trim()}>
          <Text style={styles.primaryButtonText}>{sending ? 'Sending...' : 'Send message'}</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

function TasksTab({ taskData }) {
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
              <View style={[styles.badge, task.completed ? styles.badgeMuted : null]}>
                <Text style={styles.badgeText}>{task.completed ? 'Done' : 'Pending'}</Text>
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
              <View style={[styles.badge, !job.is_active ? styles.badgeMuted : null]}>
                <Text style={styles.badgeText}>{job.is_active ? 'Active' : 'Paused'}</Text>
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
  overview,
  error,
}) {
  const pluginEntries = Object.entries(settingsData?.plugins || {});

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
        <Text style={styles.panelTitle}>Model routing</Text>
        <View style={styles.settingRow}>
          <Text style={styles.settingTitle}>Primary</Text>
          <Text style={styles.settingValue}>{settingsData?.models?.primary || 'Unavailable'}</Text>
        </View>
        <View style={styles.settingRow}>
          <Text style={styles.settingTitle}>Fast</Text>
          <Text style={styles.settingValue}>{settingsData?.models?.fast || 'Off'}</Text>
        </View>
        <View style={styles.settingRow}>
          <Text style={styles.settingTitle}>Smart</Text>
          <Text style={styles.settingValue}>{settingsData?.models?.smart || 'Unavailable'}</Text>
        </View>
      </View>

      <View style={styles.panel}>
        <Text style={styles.panelTitle}>Plugins</Text>
        {pluginEntries.length ? (
          pluginEntries.map(([key, enabled]) => (
            <View key={key} style={styles.settingRow}>
              <Text style={styles.settingTitle}>{key.replace('ENABLE_', '').replaceAll('_', ' ')}</Text>
              <Text style={styles.settingValue}>{enabled ? 'On' : 'Off'}</Text>
            </View>
          ))
        ) : (
          <EmptyState title="No settings yet" body="Load live data to see your actual runtime toggles." />
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
  const [overview, setOverview] = useState(null);
  const [taskData, setTaskData] = useState(null);
  const [buildsData, setBuildsData] = useState(null);
  const [mobileAppsData, setMobileAppsData] = useState(null);
  const [settingsData, setSettingsData] = useState(null);
  const [chatMessages, setChatMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [sending, setSending] = useState(false);
  const [actionBusy, setActionBusy] = useState('');
  const [error, setError] = useState('');
  const [bootstrapped, setBootstrapped] = useState(false);

  const headers = useMemo(
    () => ({
      'Content-Type': 'application/json',
      'X-Dashboard-Password': password,
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

  async function loadAll(showSpinner = true) {
    if (!normalizeBaseUrl(baseUrl) || !password.trim() || !userId.trim()) {
      setError('Base URL, password, and user id are required.');
      return;
    }
    if (showSpinner) {
      setLoading(true);
    }
    setError('');
    try {
      const [overviewRes, taskRes, buildsRes, appsRes, settingsRes, chatRes] = await Promise.all([
        apiGet('/api/mobile/overview'),
        apiGet('/api/mobile/tasks'),
        apiGet('/api/mobile/builds'),
        apiGet('/api/mobile/mobile-apps'),
        apiGet('/api/mobile/settings'),
        apiGet(`/api/mobile/chat/${encodeURIComponent(userId.trim())}`),
      ]);
      setOverview(overviewRes);
      setTaskData(taskRes);
      setBuildsData(buildsRes);
      setMobileAppsData(appsRes);
      setSettingsData(settingsRes);
      setChatMessages(chatRes.messages || []);
    } catch (fetchError) {
      setError(fetchError.message || 'Failed to load live data.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  async function onRefresh() {
    setRefreshing(true);
    await loadAll(false);
  }

  async function sendMessage() {
    const text = draft.trim();
    if (!text) {
      return;
    }
    setSending(true);
    setError('');
    try {
      const response = await fetch(
        `${normalizeBaseUrl(baseUrl)}/api/chat/${encodeURIComponent(userId.trim())}/send`,
        {
          method: 'POST',
          headers,
          body: JSON.stringify({ message: text }),
        }
      );
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || `Send failed: ${response.status}`);
      }
      const now = new Date().toISOString();
      setChatMessages((current) => [
        ...current,
        { role: 'user', content: text, ts: now },
        { role: 'assistant', content: data.reply, ts: new Date().toISOString() },
      ]);
      setDraft('');
      await loadAll(false);
    } catch (sendError) {
      setError(sendError.message || 'Failed to send message.');
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
          loading={loading}
          error={error}
        />
      );
    }

    switch (activeTab) {
      case 'tasks':
        return <TasksTab taskData={taskData} />;
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
            loading={loading}
            settingsData={settingsData}
            overview={overview}
            error={error}
          />
        );
      case 'chat':
      default:
        return (
          <ChatTab
            overview={overview}
            chatMessages={chatMessages}
            draft={draft}
            setDraft={setDraft}
            onSend={sendMessage}
            sending={sending}
            userId={userId.trim() || 'mobile'}
          />
        );
    }
  })();

  useEffect(() => {
    let mounted = true;
    async function bootstrap() {
      try {
        const raw = await AsyncStorage.getItem(STORAGE_KEY);
        if (raw && mounted) {
          const saved = JSON.parse(raw);
          if (saved.baseUrl) setBaseUrl(saved.baseUrl);
          if (saved.password) setPassword(saved.password);
          if (saved.userId) setUserId(saved.userId);
          if (saved.baseUrl && saved.password && saved.userId) {
            setTimeout(() => {
              loadAll(true);
            }, 0);
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
    paddingBottom: 28,
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
});
