import { NativeModules, Platform } from 'react-native';

const MODULE_NAME = 'NinoclawAndroidAgent';
const nativeModule = NativeModules[MODULE_NAME];

function unavailableStatus(summary) {
  return {
    available: false,
    requiresDevBuild: true,
    platform: Platform.OS,
    serviceEnabled: false,
    canReadScreen: false,
    canPerformGlobalActions: false,
    canTap: false,
    canTypeText: false,
    supportedActions: [],
    visibleTexts: [],
    setupSteps: [
      'Install a custom Android dev build or APK for Ninoclaw Companion.',
      'Open Android accessibility settings and enable the Ninoclaw accessibility service.',
      'Return to the app and refresh Android agent status.',
    ],
    summary,
  };
}

function missingModuleSummary() {
  if (Platform.OS !== 'android') {
    return 'Android agent is only available on Android.';
  }
  return 'Android agent native module is not available in this build. Install a custom dev build or APK; Expo Go cannot load it.';
}

export async function getAndroidAgentStatus() {
  if (!nativeModule?.getStatus) {
    return unavailableStatus(missingModuleSummary());
  }
  try {
    const status = await nativeModule.getStatus();
    return {
      ...unavailableStatus(missingModuleSummary()),
      ...(status || {}),
      available: true,
    };
  } catch (error) {
    return unavailableStatus(error?.message || 'Failed to read Android agent status.');
  }
}

export async function openAndroidAccessibilitySettings() {
  if (!nativeModule?.openAccessibilitySettings) {
    return {
      ok: false,
      summary: missingModuleSummary(),
      status: await getAndroidAgentStatus(),
    };
  }
  try {
    const result = await nativeModule.openAccessibilitySettings();
    return {
      ok: !!result?.ok,
      summary: result?.summary || 'Opened Android accessibility settings.',
      status: await getAndroidAgentStatus(),
    };
  } catch (error) {
    return {
      ok: false,
      summary: error?.message || 'Failed to open Android accessibility settings.',
      status: await getAndroidAgentStatus(),
    };
  }
}

export async function performAndroidAgentAction(action, payload = {}) {
  if (!nativeModule?.performAction) {
    return {
      ok: false,
      action,
      summary: missingModuleSummary(),
      status: await getAndroidAgentStatus(),
    };
  }
  try {
    const result = await nativeModule.performAction(action, payload || {});
    return {
      action,
      ...(result || {}),
      status: result?.status || (await getAndroidAgentStatus()),
    };
  } catch (error) {
    return {
      ok: false,
      action,
      summary: error?.message || `Android agent action failed: ${action}`,
      status: await getAndroidAgentStatus(),
    };
  }
}
