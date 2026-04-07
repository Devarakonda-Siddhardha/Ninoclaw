const fs = require('fs');
const path = require('path');
const {
  AndroidConfig,
  createRunOncePlugin,
  withAndroidManifest,
  withDangerousMod,
  withMainApplication,
} = require('@expo/config-plugins');

const SERVICE_NAME = 'NinoclawAccessibilityService';
const MODULE_NAME = 'NinoclawAndroidAgentModule';
const PACKAGE_NAME = 'NinoclawAndroidAgentPackage';

function ensureDir(target) {
  fs.mkdirSync(target, { recursive: true });
}

function writeFileIfChanged(targetPath, contents) {
  ensureDir(path.dirname(targetPath));
  const existing = fs.existsSync(targetPath) ? fs.readFileSync(targetPath, 'utf8') : null;
  if (existing !== contents) {
    fs.writeFileSync(targetPath, contents);
  }
}

function networkSecurityConfigXml() {
  return `<?xml version="1.0" encoding="utf-8"?>
<network-security-config>
  <base-config cleartextTrafficPermitted="true">
    <trust-anchors>
      <certificates src="system" />
    </trust-anchors>
  </base-config>
</network-security-config>
`;
}

function serviceXml() {
  return `<?xml version="1.0" encoding="utf-8"?>
<accessibility-service xmlns:android="http://schemas.android.com/apk/res/android"
    android:accessibilityEventTypes="typeWindowStateChanged|typeWindowContentChanged|typeViewFocused|typeViewClicked"
    android:accessibilityFeedbackType="feedbackGeneric"
    android:notificationTimeout="100"
    android:canRetrieveWindowContent="true"
    android:canPerformGestures="true"
    android:accessibilityFlags="flagReportViewIds|flagRetrieveInteractiveWindows" />
`;
}

function accessibilityServiceJava(packageName) {
  return `package ${packageName}.ninoclaw;

import android.accessibilityservice.AccessibilityService;
import android.accessibilityservice.AccessibilityServiceInfo;
import android.accessibilityservice.GestureDescription;
import android.graphics.Path;
import android.graphics.Rect;
import android.os.Bundle;
import android.os.Build;
import android.view.accessibility.AccessibilityEvent;
import android.view.accessibility.AccessibilityNodeInfo;

import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;

public class ${SERVICE_NAME} extends AccessibilityService {
    private static ${SERVICE_NAME} instance;
    private static String lastPackageName = "";
    private static String lastWindowTitle = "";
    private static long lastEventAt = 0L;
    private static ArrayList<String> lastVisibleTexts = new ArrayList<>();

    public static ${SERVICE_NAME} getInstance() {
        return instance;
    }

    public static boolean isRunning() {
        return instance != null;
    }

    public static String getLastPackageName() {
        return lastPackageName == null ? "" : lastPackageName;
    }

    public static String getLastWindowTitle() {
        return lastWindowTitle == null ? "" : lastWindowTitle;
    }

    public static long getLastEventAt() {
        return lastEventAt;
    }

    public static ArrayList<String> getLastVisibleTexts() {
        return new ArrayList<>(lastVisibleTexts);
    }

    public AccessibilityNodeInfo getRootSnapshot() {
        return getRootInActiveWindow();
    }

    @Override
    protected void onServiceConnected() {
        super.onServiceConnected();
        instance = this;
        AccessibilityServiceInfo info = getServiceInfo();
        if (info != null) {
            info.flags |= AccessibilityServiceInfo.FLAG_REPORT_VIEW_IDS;
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
                info.flags |= AccessibilityServiceInfo.FLAG_RETRIEVE_INTERACTIVE_WINDOWS;
            }
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
                info.flags |= AccessibilityServiceInfo.FLAG_INCLUDE_NOT_IMPORTANT_VIEWS;
            }
            setServiceInfo(info);
        }
    }

    @Override
    public void onAccessibilityEvent(AccessibilityEvent event) {
        if (event == null) {
            return;
        }
        CharSequence pkg = event.getPackageName();
        CharSequence title = event.getContentDescription();
        lastPackageName = pkg == null ? "" : pkg.toString();
        lastWindowTitle = title == null ? "" : title.toString();
        lastEventAt = System.currentTimeMillis();
        AccessibilityNodeInfo root = getRootInActiveWindow();
        lastVisibleTexts = collectTexts(root);
    }

    @Override
    public void onInterrupt() {
    }

    @Override
    public boolean onUnbind(android.content.Intent intent) {
        instance = null;
        return super.onUnbind(intent);
    }

    private static ArrayList<String> collectTexts(AccessibilityNodeInfo root) {
        LinkedHashSet<String> values = new LinkedHashSet<>();
        traverse(root, values, 0);
        return new ArrayList<>(values);
    }

    private static void traverse(AccessibilityNodeInfo node, Set<String> values, int depth) {
        if (node == null || depth > 30 || values.size() >= 32) {
            return;
        }
        CharSequence text = node.getText();
        if (text != null) {
            String cleaned = text.toString().trim();
            if (!cleaned.isEmpty()) {
                values.add(cleaned);
            }
        }
        CharSequence desc = node.getContentDescription();
        if (desc != null) {
            String cleaned = desc.toString().trim();
            if (!cleaned.isEmpty()) {
                values.add(cleaned);
            }
        }
        for (int i = 0; i < node.getChildCount(); i++) {
            traverse(node.getChild(i), values, depth + 1);
        }
    }

    public boolean tapBySelector(String text, String contentDescription, String viewId) {
        AccessibilityNodeInfo root = getRootInActiveWindow();
        AccessibilityNodeInfo node = findBestNode(root, text, contentDescription, viewId, false);
        if (node == null) {
            return false;
        }
        return clickNodeOrAncestor(node);
    }

    public boolean tapAt(float x, float y) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.N) {
            return false;
        }
        Path path = new Path();
        path.moveTo(x, y);
        GestureDescription.StrokeDescription stroke = new GestureDescription.StrokeDescription(path, 0, 80);
        GestureDescription gesture = new GestureDescription.Builder().addStroke(stroke).build();
        return dispatchGesture(gesture, null, null);
    }

    public boolean typeText(String text, String targetText, String contentDescription, String viewId, boolean clearExisting) {
        if (text == null || text.trim().isEmpty()) {
            return false;
        }
        AccessibilityNodeInfo root = getRootInActiveWindow();
        AccessibilityNodeInfo node = findBestNode(root, targetText, contentDescription, viewId, true);
        if (node == null) {
            node = findFocusedEditableNode(root);
        }
        if (node == null) {
            return false;
        }
        if (clearExisting && Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
            Bundle clearArgs = new Bundle();
            clearArgs.putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE, "");
            node.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, clearArgs);
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
            Bundle arguments = new Bundle();
            arguments.putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE, text);
            boolean set = node.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, arguments);
            if (set) {
                return true;
            }
        }
        Bundle pasteArgs = new Bundle();
        pasteArgs.putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE, text);
        return node.performAction(AccessibilityNodeInfo.ACTION_FOCUS) && node.performAction(AccessibilityNodeInfo.ACTION_PASTE, pasteArgs);
    }

    private AccessibilityNodeInfo findFocusedEditableNode(AccessibilityNodeInfo root) {
        if (root == null) {
            return null;
        }
        if (root.isEditable() && (root.isFocused() || root.isAccessibilityFocused() || root.isFocusable())) {
            return root;
        }
        for (int i = 0; i < root.getChildCount(); i++) {
            AccessibilityNodeInfo child = root.getChild(i);
            AccessibilityNodeInfo found = findFocusedEditableNode(child);
            if (found != null) {
                return found;
            }
        }
        return null;
    }

    private AccessibilityNodeInfo findBestNode(AccessibilityNodeInfo root, String text, String contentDescription, String viewId, boolean requireEditable) {
        AccessibilityNodeInfo byViewId = findByViewId(root, viewId, requireEditable);
        if (byViewId != null) {
            return byViewId;
        }
        AccessibilityNodeInfo byText = findByText(root, text, requireEditable);
        if (byText != null) {
            return byText;
        }
        AccessibilityNodeInfo byDesc = findByContentDescription(root, contentDescription, requireEditable);
        if (byDesc != null) {
            return byDesc;
        }
        return requireEditable ? findFirstEditable(root) : null;
    }

    private AccessibilityNodeInfo findByViewId(AccessibilityNodeInfo root, String viewId, boolean requireEditable) {
        if (root == null || viewId == null || viewId.trim().isEmpty() || Build.VERSION.SDK_INT < Build.VERSION_CODES.JELLY_BEAN_MR2) {
            return null;
        }
        List<AccessibilityNodeInfo> nodes = root.findAccessibilityNodeInfosByViewId(viewId);
        if (nodes == null) {
            return null;
        }
        for (AccessibilityNodeInfo node : nodes) {
            if (node == null) {
                continue;
            }
            if (!requireEditable || node.isEditable()) {
                return node;
            }
        }
        return null;
    }

    private AccessibilityNodeInfo findByText(AccessibilityNodeInfo root, String text, boolean requireEditable) {
        if (root == null || text == null || text.trim().isEmpty()) {
            return null;
        }
        List<AccessibilityNodeInfo> nodes = root.findAccessibilityNodeInfosByText(text);
        if (nodes == null) {
            return null;
        }
        String wanted = text.trim().toLowerCase();
        AccessibilityNodeInfo partial = null;
        for (AccessibilityNodeInfo node : nodes) {
            if (node == null) {
                continue;
            }
            if (requireEditable && !node.isEditable()) {
                continue;
            }
            CharSequence label = node.getText();
            String normalized = label == null ? "" : label.toString().trim().toLowerCase();
            if (normalized.equals(wanted)) {
                return node;
            }
            if (partial == null) {
                partial = node;
            }
        }
        return partial;
    }

    private AccessibilityNodeInfo findByContentDescription(AccessibilityNodeInfo root, String text, boolean requireEditable) {
        if (root == null || text == null || text.trim().isEmpty()) {
            return null;
        }
        String wanted = text.trim().toLowerCase();
        if (root.getContentDescription() != null) {
            String description = root.getContentDescription().toString().trim().toLowerCase();
            if (description.contains(wanted) && (!requireEditable || root.isEditable())) {
                return root;
            }
        }
        for (int i = 0; i < root.getChildCount(); i++) {
            AccessibilityNodeInfo child = root.getChild(i);
            AccessibilityNodeInfo found = findByContentDescription(child, text, requireEditable);
            if (found != null) {
                return found;
            }
        }
        return null;
    }

    private AccessibilityNodeInfo findFirstEditable(AccessibilityNodeInfo root) {
        if (root == null) {
            return null;
        }
        if (root.isEditable()) {
            return root;
        }
        for (int i = 0; i < root.getChildCount(); i++) {
            AccessibilityNodeInfo child = root.getChild(i);
            AccessibilityNodeInfo found = findFirstEditable(child);
            if (found != null) {
                return found;
            }
        }
        return null;
    }

    private boolean clickNodeOrAncestor(AccessibilityNodeInfo node) {
        AccessibilityNodeInfo current = node;
        while (current != null) {
            if (current.isClickable() && current.performAction(AccessibilityNodeInfo.ACTION_CLICK)) {
                return true;
            }
            Rect bounds = new Rect();
            current.getBoundsInScreen(bounds);
            if (!bounds.isEmpty()) {
                float x = bounds.centerX();
                float y = bounds.centerY();
                if (tapAt(x, y)) {
                    return true;
                }
            }
            current = current.getParent();
        }
        return false;
    }
}
`;
}

function moduleJava(packageName) {
  return `package ${packageName}.ninoclaw;

import android.accessibilityservice.AccessibilityService;
import android.content.Intent;
import android.os.Build;
import android.provider.Settings;

import androidx.annotation.NonNull;

import com.facebook.react.bridge.Arguments;
import com.facebook.react.bridge.Promise;
import com.facebook.react.bridge.ReactApplicationContext;
import com.facebook.react.bridge.ReactContextBaseJavaModule;
import com.facebook.react.bridge.ReactMethod;
import com.facebook.react.bridge.ReadableMap;
import com.facebook.react.bridge.WritableArray;
import com.facebook.react.bridge.WritableMap;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

public class ${MODULE_NAME} extends ReactContextBaseJavaModule {
    private final ReactApplicationContext reactContext;

    public ${MODULE_NAME}(ReactApplicationContext reactContext) {
        super(reactContext);
        this.reactContext = reactContext;
    }

    @NonNull
    @Override
    public String getName() {
        return "NinoclawAndroidAgent";
    }

    @ReactMethod
    public void getStatus(Promise promise) {
        promise.resolve(buildStatusMap());
    }

    @ReactMethod
    public void openAccessibilitySettings(Promise promise) {
        try {
            Intent intent = new Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS);
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            reactContext.startActivity(intent);
            WritableMap result = Arguments.createMap();
            result.putBoolean("ok", true);
            result.putString("summary", "Opened Android accessibility settings.");
            promise.resolve(result);
        } catch (Exception e) {
            promise.reject("open_accessibility_settings_failed", e);
        }
    }

    @ReactMethod
    public void performAction(String action, ReadableMap payload, Promise promise) {
        WritableMap result = Arguments.createMap();
        result.putString("action", action == null ? "" : action);

        try {
            ${SERVICE_NAME} service = ${SERVICE_NAME}.getInstance();
            if (service == null) {
                result.putBoolean("ok", false);
                result.putString("summary", "Accessibility service is not enabled.");
                result.putMap("status", buildStatusMap());
                promise.resolve(result);
                return;
            }
            if ("press_back".equals(action)) {
                boolean ok = performGlobalAction(AccessibilityService.GLOBAL_ACTION_BACK);
                result.putBoolean("ok", ok);
                result.putString("summary", ok ? "Pressed Back via accessibility service." : "Accessibility service is not enabled.");
                result.putMap("status", buildStatusMap());
                promise.resolve(result);
                return;
            }
            if ("open_notifications".equals(action)) {
                boolean ok = performGlobalAction(AccessibilityService.GLOBAL_ACTION_NOTIFICATIONS);
                result.putBoolean("ok", ok);
                result.putString("summary", ok ? "Opened notification shade." : "Accessibility service is not enabled.");
                result.putMap("status", buildStatusMap());
                promise.resolve(result);
                return;
            }
            if ("open_quick_settings".equals(action)) {
                boolean ok = performGlobalAction(AccessibilityService.GLOBAL_ACTION_QUICK_SETTINGS);
                result.putBoolean("ok", ok);
                result.putString("summary", ok ? "Opened quick settings." : "Accessibility service is not enabled.");
                result.putMap("status", buildStatusMap());
                promise.resolve(result);
                return;
            }
            if ("read_screen".equals(action)) {
                result.putBoolean("ok", true);
                result.putString("summary", "Collected latest accessibility snapshot.");
                result.putMap("status", buildStatusMap());
                promise.resolve(result);
                return;
            }
            if ("tap".equals(action) || "type_text".equals(action)) {
                if ("tap".equals(action)) {
                    boolean usedCoords = payload != null && payload.hasKey("x") && payload.hasKey("y");
                    boolean ok;
                    if (usedCoords) {
                        float x = (float) payload.getDouble("x");
                        float y = (float) payload.getDouble("y");
                        ok = service.tapAt(x, y);
                        result.putBoolean("ok", ok);
                        result.putString("summary", ok ? "Tapped screen coordinates via accessibility gesture." : "Could not tap the requested coordinates.");
                    } else {
                        String text = readString(payload, "text", "label", "selectorText");
                        String description = readString(payload, "contentDescription", "description", "content_desc");
                        String viewId = readString(payload, "viewId", "view_id", "resourceId");
                        ok = service.tapBySelector(text, description, viewId);
                        result.putBoolean("ok", ok);
                        result.putString("summary", ok ? "Tapped matching screen element." : "Could not find a tappable element matching the selector.");
                    }
                    result.putMap("status", buildStatusMap());
                    promise.resolve(result);
                    return;
                }
                String textToType = readString(payload, "text", "value", "message");
                String targetText = readString(payload, "targetText", "target_text", "label", "placeholder");
                String description = readString(payload, "contentDescription", "description", "content_desc");
                String viewId = readString(payload, "viewId", "view_id", "resourceId");
                boolean clearExisting = payload != null && payload.hasKey("clearExisting") ? payload.getBoolean("clearExisting") : true;
                boolean ok = service.typeText(textToType, targetText, description, viewId, clearExisting);
                result.putBoolean("ok", ok);
                result.putString("summary", ok ? "Typed text into the matched input field." : "Could not find an editable field for text input.");
                result.putMap("status", buildStatusMap());
                promise.resolve(result);
                return;
            }
            result.putBoolean("ok", false);
            result.putString("summary", "Unsupported Android agent action: " + action);
            result.putMap("status", buildStatusMap());
            promise.resolve(result);
        } catch (Exception e) {
            promise.reject("android_agent_action_failed", e);
        }
    }

    private boolean performGlobalAction(int action) {
        ${SERVICE_NAME} service = ${SERVICE_NAME}.getInstance();
        return service != null && service.performGlobalAction(action);
    }

    private String readString(ReadableMap payload, String... keys) {
        if (payload == null) {
            return "";
        }
        for (String key : keys) {
            if (payload.hasKey(key) && !payload.isNull(key)) {
                try {
                    String value = payload.getString(key);
                    if (value != null && !value.trim().isEmpty()) {
                        return value.trim();
                    }
                } catch (Exception ignored) {
                }
            }
        }
        return "";
    }

    private WritableMap buildStatusMap() {
        WritableMap map = Arguments.createMap();
        boolean running = ${SERVICE_NAME}.isRunning();
        map.putBoolean("available", true);
        map.putBoolean("requiresDevBuild", true);
        map.putString("platform", "android");
        map.putBoolean("serviceEnabled", running);
        map.putBoolean("canReadScreen", running);
        map.putBoolean("canPerformGlobalActions", running);
        map.putBoolean("canTap", running && Build.VERSION.SDK_INT >= Build.VERSION_CODES.N);
        map.putBoolean("canTypeText", running && Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP);
        map.putString("lastPackageName", ${SERVICE_NAME}.getLastPackageName());
        map.putString("lastWindowTitle", ${SERVICE_NAME}.getLastWindowTitle());
        map.putDouble("lastEventAt", (double) ${SERVICE_NAME}.getLastEventAt());
        WritableArray supported = Arguments.createArray();
        for (String action : Arrays.asList("press_back", "open_notifications", "open_quick_settings", "read_screen", "tap", "type_text")) {
            supported.pushString(action);
        }
        WritableArray texts = Arguments.createArray();
        for (String value : ${SERVICE_NAME}.getLastVisibleTexts()) {
            texts.pushString(value);
        }
        WritableArray setupSteps = Arguments.createArray();
        setupSteps.pushString("Install a custom Android dev build or APK for Ninoclaw Companion.");
        setupSteps.pushString("Open Android accessibility settings and enable the Ninoclaw accessibility service.");
        setupSteps.pushString("Return to the app and refresh Android agent status.");
        map.putArray("supportedActions", supported);
        map.putArray("visibleTexts", texts);
        map.putArray("setupSteps", setupSteps);
        return map;
    }
}
`;
}

function packageJava(packageName) {
  return `package ${packageName}.ninoclaw;

import androidx.annotation.NonNull;

import com.facebook.react.ReactPackage;
import com.facebook.react.bridge.NativeModule;
import com.facebook.react.bridge.ReactApplicationContext;
import com.facebook.react.uimanager.ViewManager;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

public class ${PACKAGE_NAME} implements ReactPackage {
    @NonNull
    @Override
    public List<NativeModule> createNativeModules(@NonNull ReactApplicationContext reactContext) {
        List<NativeModule> modules = new ArrayList<>();
        modules.add(new ${MODULE_NAME}(reactContext));
        return modules;
    }

    @NonNull
    @Override
    public List<ViewManager> createViewManagers(@NonNull ReactApplicationContext reactContext) {
        return Collections.emptyList();
    }
}
`;
}

function addServiceToManifest(config) {
  return withAndroidManifest(config, (mod) => {
    const manifest = mod.modResults;
    let app;
    try {
      app = AndroidConfig.Manifest.getMainApplicationOrThrow(manifest);
    } catch (_error) {
      app = manifest?.manifest?.application?.[0];
    }
    if (!app) {
      throw new Error('Ninoclaw Android agent plugin could not find the Android <application> element during prebuild.');
    }
    app.$['android:networkSecurityConfig'] = '@xml/network_security_config';
    app.service = app.service || [];
    const alreadyPresent = app.service.some((entry) => entry.$['android:name'] === `.${SERVICE_NAME}` || entry.$['android:name']?.endsWith(`.${SERVICE_NAME}`));
    if (!alreadyPresent) {
      app.service.push({
        $: {
          'android:name': `.ninoclaw.${SERVICE_NAME}`,
          'android:permission': 'android.permission.BIND_ACCESSIBILITY_SERVICE',
          'android:exported': 'false',
          'android:label': 'Ninoclaw Accessibility Agent',
        },
        'intent-filter': [
          {
            action: [
              {
                $: {
                  'android:name': 'android.accessibilityservice.AccessibilityService',
                },
              },
            ],
          },
        ],
        'meta-data': [
          {
            $: {
              'android:name': 'android.accessibilityservice',
              'android:resource': '@xml/ninoclaw_accessibility_service',
            },
          },
        ],
      });
    }
    return mod;
  });
}

function writeNativeFiles(config) {
  return withDangerousMod(config, [
    'android',
    async (mod) => {
      const applicationId = config.android?.package || 'com.ninoclaw.companion';
      const projectRoot = mod.modRequest.projectRoot;
      const sourceDir = path.join(
        projectRoot,
        'android',
        'app',
        'src',
        'main',
        'java',
        ...applicationId.split('.'),
        'ninoclaw'
      );
      const xmlDir = path.join(projectRoot, 'android', 'app', 'src', 'main', 'res', 'xml');
      writeFileIfChanged(path.join(sourceDir, `${SERVICE_NAME}.java`), accessibilityServiceJava(applicationId));
      writeFileIfChanged(path.join(sourceDir, `${MODULE_NAME}.java`), moduleJava(applicationId));
      writeFileIfChanged(path.join(sourceDir, `${PACKAGE_NAME}.java`), packageJava(applicationId));
      writeFileIfChanged(path.join(xmlDir, 'ninoclaw_accessibility_service.xml'), serviceXml());
      writeFileIfChanged(path.join(xmlDir, 'network_security_config.xml'), networkSecurityConfigXml());
      return mod;
    },
  ]);
}

function patchMainApplication(config) {
  return withMainApplication(config, (mod) => {
    const packageName = config.android?.package || 'com.ninoclaw.companion';
    const importLine = `import ${packageName}.ninoclaw.${PACKAGE_NAME};`;
    let contents = mod.modResults.contents;

    if (!contents.includes(importLine)) {
      contents = contents.replace(/package .*?;\n/, (match) => `${match}${importLine}\n`);
    }

    if (mod.modResults.language === 'java') {
      if (!contents.includes('new NinoclawAndroidAgentPackage()')) {
        contents = contents.replace(
          /return packages;/,
          'packages.add(new NinoclawAndroidAgentPackage());\n      return packages;'
        );
      }
    } else {
      if (!contents.includes('NinoclawAndroidAgentPackage()')) {
        contents = contents.replace(
          /return packages/,
          'packages.add(NinoclawAndroidAgentPackage())\n      return packages'
        );
      }
    }

    mod.modResults.contents = contents;
    return mod;
  });
}

const withNinoclawAndroidAgent = (config) => {
  config = addServiceToManifest(config);
  config = writeNativeFiles(config);
  config = patchMainApplication(config);
  return config;
};

module.exports = createRunOncePlugin(withNinoclawAndroidAgent, 'with-ninoclaw-android-agent', '1.0.0');
