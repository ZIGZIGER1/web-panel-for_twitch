const state = {
  data: null,
  frameVersion: -1,
  hydrated: false,
  activeView: "home",
  previewLoading: false,
  pendingPreviewUrl: "",
  activePreviewUrl: "",
  eventSource: null,
  eventRetryTimer: null,
  liveRefreshTimer: null,
  stateRefreshTimer: null,
};

const els = {
  heroSceneChip: document.getElementById("heroSceneChip"),
  heroChatChip: document.getElementById("heroChatChip"),
  heroSignalChip: document.getElementById("heroSignalChip"),
  heroSignalStat: document.getElementById("heroSignalStat"),
  overlayShort: document.getElementById("overlayShort"),
  chatShort: document.getElementById("chatShort"),
  sceneSizeStat: document.getElementById("sceneSizeStat"),
  presetNote: document.getElementById("presetNote"),
  captureHint: document.getElementById("captureHint"),
  sceneMeta: document.getElementById("sceneMeta"),
  chatStatusText: document.getElementById("chatStatusText"),
  tuneStatusText: document.getElementById("tuneStatusText"),
  audioStatusText: document.getElementById("audioStatusText"),
  obsHelpText: document.getElementById("obsHelpText"),
  statusAudioLine: document.getElementById("statusAudioLine"),
  statusChatLine: document.getElementById("statusChatLine"),
  statusErrorsLine: document.getElementById("statusErrorsLine"),
  overlayRouteInput: document.getElementById("overlayRouteInput"),
  chatRouteInput: document.getElementById("chatRouteInput"),
  overlayRouteChip: document.getElementById("overlayRouteChip"),
  chatRouteChip: document.getElementById("chatRouteChip"),
  heroScenePill: document.getElementById("heroScenePill"),
  heroChatPill: document.getElementById("heroChatPill"),
  heroSignalPill: document.getElementById("heroSignalPill"),
  frameImage: document.getElementById("frameImage"),
  framePreviewImages: Array.from(document.querySelectorAll("[data-frame-preview]")),
  micLevelValue: document.getElementById("micLevelValue"),
  micLevelFill: document.getElementById("micLevelFill"),
  audioPreviewLevelValue: document.getElementById("audioPreviewLevelValue"),
  audioPreviewLevelFill: document.getElementById("audioPreviewLevelFill"),
  thresholdValue: document.getElementById("thresholdValue"),
  tuneAutoThresholdValue: document.getElementById("tuneAutoThresholdValue"),
  tuneAutoFloorValue: document.getElementById("tuneAutoFloorValue"),
  tuneAutoReleaseValue: document.getElementById("tuneAutoReleaseValue"),
  scalePercentValue: document.getElementById("scalePercentValue"),
  marginXValue: document.getElementById("marginXValue"),
  marginYValue: document.getElementById("marginYValue"),
  chatWidthPercentValue: document.getElementById("chatWidthPercentValue"),
  pulseBars: document.getElementById("pulseBars"),
  audioPreviewBars: document.getElementById("audioPreviewBars"),
  audioPreviewStatus: document.getElementById("audioPreviewStatus"),
  audioPreviewDevice: document.getElementById("audioPreviewDevice"),
  audioPreviewThreshold: document.getElementById("audioPreviewThreshold"),
  audioPreviewSignal: document.getElementById("audioPreviewSignal"),
  chatPreviewStatus: document.getElementById("chatPreviewStatus"),
  chatPreviewFrame: document.getElementById("chatPreviewFrame"),
  musicPreviewStatus: document.getElementById("musicPreviewStatus"),
  musicPlayerFrame: document.getElementById("musicPlayerFrame"),
  musicQueueFrame: document.getElementById("musicQueueFrame"),
  musicDockRouteInput: document.getElementById("musicDockRouteInput"),
  openOverlayBtn: document.getElementById("openOverlayBtn"),
  copyOverlayBtn: document.getElementById("copyOverlayBtn"),
  openChatBtn: document.getElementById("openChatBtn"),
  copyChatBtn: document.getElementById("copyChatBtn"),
  openTuneHomeBtn: document.getElementById("openTuneHomeBtn"),
  openTuneDashboardBtn: document.getElementById("openTuneDashboardBtn"),
  openTuneHomeInlineBtn: document.getElementById("openTuneHomeInlineBtn"),
  openTuneDashboardInlineBtn: document.getElementById("openTuneDashboardInlineBtn"),
  scenePreviewOpenBtn: document.getElementById("scenePreviewOpenBtn"),
  scenePreviewCopyBtn: document.getElementById("scenePreviewCopyBtn"),
  scenePreviewOpenChatBtn: document.getElementById("scenePreviewOpenChatBtn"),
  scenePreviewCopyChatBtn: document.getElementById("scenePreviewCopyChatBtn"),
  chatPreviewOpenBtn: document.getElementById("chatPreviewOpenBtn"),
  chatPreviewCopyBtn: document.getElementById("chatPreviewCopyBtn"),
  chatPreviewOpenSceneBtn: document.getElementById("chatPreviewOpenSceneBtn"),
  chatPreviewCopySceneBtn: document.getElementById("chatPreviewCopySceneBtn"),
  tunePlayerRouteInput: document.getElementById("tunePlayerRouteInput"),
  tuneQueueRouteInput: document.getElementById("tuneQueueRouteInput"),
  tuneDockRouteInput: document.getElementById("tuneDockRouteInput"),
  copyTunePlayerRouteBtn: document.getElementById("copyTunePlayerRouteBtn"),
  openTunePlayerRouteBtn: document.getElementById("openTunePlayerRouteBtn"),
  copyTunePlayerDirectBtn: document.getElementById("copyTunePlayerDirectBtn"),
  copyTuneQueueRouteBtn: document.getElementById("copyTuneQueueRouteBtn"),
  openTuneQueueRouteBtn: document.getElementById("openTuneQueueRouteBtn"),
  copyTuneQueueDirectBtn: document.getElementById("copyTuneQueueDirectBtn"),
  copyTuneDockRouteBtn: document.getElementById("copyTuneDockRouteBtn"),
  openTuneDockRouteBtn: document.getElementById("openTuneDockRouteBtn"),
  openTuneDockDirectBtn: document.getElementById("openTuneDockDirectBtn"),
  musicPreviewOpenPlayerBtn: document.getElementById("musicPreviewOpenPlayerBtn"),
  musicPreviewCopyPlayerBtn: document.getElementById("musicPreviewCopyPlayerBtn"),
  musicPreviewCopyPlayerDirectBtn: document.getElementById("musicPreviewCopyPlayerDirectBtn"),
  musicPreviewOpenQueueBtn: document.getElementById("musicPreviewOpenQueueBtn"),
  musicPreviewCopyQueueBtn: document.getElementById("musicPreviewCopyQueueBtn"),
  musicPreviewCopyQueueDirectBtn: document.getElementById("musicPreviewCopyQueueDirectBtn"),
  musicPreviewOpenDockBtn: document.getElementById("musicPreviewOpenDockBtn"),
  musicPreviewCopyDockBtn: document.getElementById("musicPreviewCopyDockBtn"),
  refreshDevicesBtn: document.getElementById("refreshDevicesBtn"),
  startAudioBtn: document.getElementById("startAudioBtn"),
  stopAudioBtn: document.getElementById("stopAudioBtn"),
  audioPreviewStartBtn: document.getElementById("audioPreviewStartBtn"),
  audioPreviewStopBtn: document.getElementById("audioPreviewStopBtn"),
  audioPreviewRefreshBtn: document.getElementById("audioPreviewRefreshBtn"),
  audioPreviewOpenSceneBtn: document.getElementById("audioPreviewOpenSceneBtn"),
};

const fieldMap = {
  internetPack: document.getElementById("internetPack"),
  streamMoment: document.getElementById("streamMoment"),
  presetLabel: document.getElementById("presetLabel"),
  imageIdle: document.getElementById("imageIdle"),
  imageTalkA: document.getElementById("imageTalkA"),
  imageTalkB: document.getElementById("imageTalkB"),
  backgroundPath: document.getElementById("backgroundPath"),
  sceneStyle: document.getElementById("sceneStyle"),
  anchorLabel: document.getElementById("anchorLabel"),
  bgMode: document.getElementById("bgMode"),
  bgColor: document.getElementById("bgColor"),
  scalePercent: document.getElementById("scalePercent"),
  marginX: document.getElementById("marginX"),
  marginY: document.getElementById("marginY"),
  showSceneFrame: document.getElementById("showSceneFrame"),
  showSceneLabel: document.getElementById("showSceneLabel"),
  showSceneRibbon: document.getElementById("showSceneRibbon"),
  chatUrl: document.getElementById("chatUrl"),
  chatAuthUser: document.getElementById("chatAuthUser"),
  chatAuthToken: document.getElementById("chatAuthToken"),
  tunePlayerUrl: document.getElementById("tunePlayerUrl"),
  tuneQueueUrl: document.getElementById("tuneQueueUrl"),
  tuneDockUrl: document.getElementById("tuneDockUrl"),
  tuneAutoMode: document.getElementById("tuneAutoMode"),
  tuneAutoThreshold: document.getElementById("tuneAutoThreshold"),
  tuneAutoFloor: document.getElementById("tuneAutoFloor"),
  tuneAutoReleaseMs: document.getElementById("tuneAutoReleaseMs"),
  tuneAutoPlayer: document.getElementById("tuneAutoPlayer"),
  tuneAutoQueue: document.getElementById("tuneAutoQueue"),
  tuneAutoDock: document.getElementById("tuneAutoDock"),
  chatStyle: document.getElementById("chatStyle"),
  chatSide: document.getElementById("chatSide"),
  chatWidthPercent: document.getElementById("chatWidthPercent"),
  chatCompactMode: document.getElementById("chatCompactMode"),
  chatRevealOnly: document.getElementById("chatRevealOnly"),
  deviceLabel: document.getElementById("deviceLabel"),
  threshold: document.getElementById("threshold"),
};

const viewButtons = Array.from(document.querySelectorAll("[data-view-btn]"));
const viewDecks = Array.from(document.querySelectorAll(".view-deck"));

const writeDebouncers = new Map();

function ensureBars() {
  document.querySelectorAll("[data-pulse-bars], #pulseBars").forEach((container) => {
    if (!container || container.children.length) return;
    for (let i = 0; i < 18; i += 1) {
      const bar = document.createElement("div");
      bar.className = "pulse-bar";
      container.appendChild(bar);
    }
  });
}

function setOptions(select, values, currentValue) {
  if (!select) return;
  const next = values.map((value) => String(value));
  const currentOptions = Array.from(select.options).map((option) => option.value);
  if (JSON.stringify(next) !== JSON.stringify(currentOptions)) {
    select.innerHTML = "";
    next.forEach((value) => {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = value;
      select.appendChild(option);
    });
  }
  if (currentValue !== undefined && select.value !== currentValue) {
    select.value = currentValue;
  }
}

async function apiGet(path) {
  const response = await fetch(path, { cache: "no-store" });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}

async function apiPost(path, payload = {}) {
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
  return data;
}

function scheduleWrite(key, value, delay = 180) {
  if (writeDebouncers.has(key)) {
    clearTimeout(writeDebouncers.get(key));
  }
  const handle = setTimeout(async () => {
    writeDebouncers.delete(key);
    try {
      const next = await apiPost("/api/settings", { [key]: value });
      applyState(next, { hydrateForm: true });
    } catch (error) {
      console.error(error);
    }
  }, delay);
  writeDebouncers.set(key, handle);
}

function hydrateChoices(data) {
  setOptions(fieldMap.internetPack, data.choices.packs, data.settings.internetPack);
  setOptions(fieldMap.streamMoment, data.choices.moments, data.settings.streamMoment);
  setOptions(fieldMap.presetLabel, data.choices.presets, data.settings.presetLabel);
  setOptions(fieldMap.sceneStyle, data.choices.sceneStyles, data.settings.sceneStyle);
  setOptions(fieldMap.chatStyle, data.choices.chatStyles, data.settings.chatStyle);
  setOptions(fieldMap.chatSide, data.choices.chatSides, data.settings.chatSide);
  setOptions(fieldMap.anchorLabel, data.choices.anchors, data.settings.anchorLabel);
  setOptions(fieldMap.deviceLabel, data.devices.available, data.devices.selected);
}

function hydrateForm(settings, devices) {
  fieldMap.internetPack.value = settings.internetPack;
  fieldMap.streamMoment.value = settings.streamMoment;
  fieldMap.presetLabel.value = settings.presetLabel;
  fieldMap.imageIdle.value = settings.imageIdle;
  fieldMap.imageTalkA.value = settings.imageTalkA;
  fieldMap.imageTalkB.value = settings.imageTalkB;
  fieldMap.backgroundPath.value = settings.backgroundPath;
  fieldMap.sceneStyle.value = settings.sceneStyle;
  fieldMap.anchorLabel.value = settings.anchorLabel;
  fieldMap.bgMode.value = settings.bgMode;
  fieldMap.bgColor.value = settings.bgColor;
  fieldMap.scalePercent.value = settings.scalePercent;
  fieldMap.marginX.value = settings.marginX;
  fieldMap.marginY.value = settings.marginY;
  fieldMap.showSceneFrame.checked = settings.showSceneFrame;
  fieldMap.showSceneLabel.checked = settings.showSceneLabel;
  fieldMap.showSceneRibbon.checked = settings.showSceneRibbon;
  fieldMap.chatUrl.value = settings.chatUrl;
  fieldMap.chatAuthUser.value = settings.chatAuthUser;
  fieldMap.chatAuthToken.value = settings.chatAuthToken;
  fieldMap.tunePlayerUrl.value = settings.tunePlayerUrl || "";
  fieldMap.tuneQueueUrl.value = settings.tuneQueueUrl || "";
  fieldMap.tuneDockUrl.value = settings.tuneDockUrl || "";
  fieldMap.tuneAutoMode.value = settings.tuneAutoMode || "off";
  fieldMap.tuneAutoThreshold.value = settings.tuneAutoThreshold ?? 18;
  fieldMap.tuneAutoFloor.value = settings.tuneAutoFloor ?? 35;
  fieldMap.tuneAutoReleaseMs.value = settings.tuneAutoReleaseMs ?? 900;
  fieldMap.tuneAutoPlayer.checked = Boolean(settings.tuneAutoPlayer);
  fieldMap.tuneAutoQueue.checked = Boolean(settings.tuneAutoQueue);
  fieldMap.tuneAutoDock.checked = Boolean(settings.tuneAutoDock);
  fieldMap.chatStyle.value = settings.chatStyle;
  fieldMap.chatSide.value = settings.chatSide;
  fieldMap.chatWidthPercent.value = settings.chatWidthPercent;
  fieldMap.chatCompactMode.checked = settings.chatCompactMode;
  fieldMap.chatRevealOnly.checked = settings.chatRevealOnly;
  fieldMap.threshold.value = settings.threshold;
  fieldMap.deviceLabel.value = devices.selected || "";

  els.thresholdValue.textContent = Math.round(settings.threshold);
  els.tuneAutoThresholdValue.textContent = `${Math.round(settings.tuneAutoThreshold ?? 18)}`;
  els.tuneAutoFloorValue.textContent = `${Math.round(settings.tuneAutoFloor ?? 35)}%`;
  els.tuneAutoReleaseValue.textContent = `${((settings.tuneAutoReleaseMs ?? 900) / 1000).toFixed(1)} c`;
  els.scalePercentValue.textContent = `${Math.round(settings.scalePercent)}%`;
  els.marginXValue.textContent = `${Math.round(settings.marginX)} px`;
  els.marginYValue.textContent = `${Math.round(settings.marginY)} px`;
  els.chatWidthPercentValue.textContent = `${Math.round(settings.chatWidthPercent)}%`;
}

function renderMeterShell(valueEl, fillEl, barsEl, level) {
  if (!valueEl || !fillEl || !barsEl) return;
  const safeLevel = Math.max(0, Math.min(100, Number(level) || 0));
  valueEl.textContent = `${Math.round(safeLevel)}%`;
  fillEl.style.width = `${safeLevel}%`;

  Array.from(barsEl.children).forEach((bar, index) => {
    const wave = Math.sin(Date.now() / 180 + index * 0.55) * 0.5 + 0.5;
    const intensity = Math.min(1, safeLevel / 100 + wave * 0.22);
    bar.style.height = `${8 + intensity * 42}px`;
    bar.style.opacity = String(0.32 + intensity * 0.68);
  });
}

function renderMeter(level) {
  renderMeterShell(els.micLevelValue, els.micLevelFill, els.pulseBars, level);
  renderMeterShell(els.audioPreviewLevelValue, els.audioPreviewLevelFill, els.audioPreviewBars, level);
}

function applySignalSnapshot(payload = {}) {
  const signalText = String(payload.heroSignal || "").trim();
  const audioLevel = Number(payload.audioLevel);

  if (signalText) {
    els.heroSignalChip.textContent = signalText;
    els.heroSignalStat.textContent = signalText;
    els.heroSignalPill.textContent = signalText;
  }

  if (Number.isFinite(audioLevel)) {
    renderMeter(audioLevel);
  }
}

function copyText(text) {
  if (!text) return;
  navigator.clipboard.writeText(text).catch(() => {});
}

function openUrl(url) {
  if (!url) return;
  window.open(url, "_blank", "noopener,noreferrer");
}

function syncEmbedSource(frame, url) {
  if (!frame || !url) return;
  if (frame.dataset.src === url) return;
  frame.dataset.src = url;
  frame.src = url;
}

function applyView(view) {
  state.activeView = view;
  viewButtons.forEach((button) => {
    button.classList.toggle("is-active", button.dataset.viewBtn === view);
  });

  viewDecks.forEach((deck) => {
    const views = String(deck.dataset.view || "").split(/\s+/).filter(Boolean);
    const show = views.includes(view);
    deck.classList.toggle("is-hidden", !show);
  });
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function buildPreviewUrl(sessionId, frameVersion) {
  const sid = encodeURIComponent(sessionId || state.data?.sessionId || "preview");
  return `/frame.png?sid=${sid}&v=${frameVersion}`;
}

function pumpPreviewQueue() {
  if (state.previewLoading || !state.pendingPreviewUrl) return;

  const nextUrl = state.pendingPreviewUrl;
  state.pendingPreviewUrl = "";
  state.previewLoading = true;

  const image = new Image();
  image.decoding = "async";
  image.onload = () => {
    els.framePreviewImages.forEach((previewImage) => {
      previewImage.style.opacity = "0.9";
      previewImage.src = nextUrl;
      requestAnimationFrame(() => {
        previewImage.style.opacity = "1";
      });
    });
    state.activePreviewUrl = nextUrl;
    state.previewLoading = false;
    if (state.pendingPreviewUrl && state.pendingPreviewUrl !== state.activePreviewUrl) {
      pumpPreviewQueue();
    }
  };
  image.onerror = () => {
    state.previewLoading = false;
    if (state.pendingPreviewUrl && state.pendingPreviewUrl !== state.activePreviewUrl) {
      setTimeout(pumpPreviewQueue, 80);
    }
  };
  image.src = nextUrl;
}

function queuePreviewFrame(sessionId, frameVersion) {
  const nextUrl = buildPreviewUrl(sessionId, frameVersion);
  if (nextUrl === state.activePreviewUrl || nextUrl === state.pendingPreviewUrl) return;
  state.pendingPreviewUrl = nextUrl;
  pumpPreviewQueue();
}

function connectPreviewEvents() {
  if (state.eventSource) {
    state.eventSource.close();
    state.eventSource = null;
  }
  if (state.eventRetryTimer) {
    clearTimeout(state.eventRetryTimer);
    state.eventRetryTimer = null;
  }

  const source = new EventSource("/api/events");
  state.eventSource = source;

  const handleFrameEvent = (event) => {
    try {
      const payload = JSON.parse(event.data || "{}");
      const nextFrameVersion = Number(payload.frameVersion || 0);
      if (!Number.isFinite(nextFrameVersion) || nextFrameVersion <= 0) return;
      if (nextFrameVersion > state.frameVersion) {
        state.frameVersion = nextFrameVersion;
      }
      queuePreviewFrame(payload.sessionId, nextFrameVersion);
    } catch (error) {
      console.error(error);
    }
  };

  const handleSignalEvent = (event) => {
    try {
      const payload = JSON.parse(event.data || "{}");
      applySignalSnapshot(payload);
    } catch (error) {
      console.error(error);
    }
  };

  source.addEventListener("hello", (event) => {
    handleFrameEvent(event);
    handleSignalEvent(event);
  });
  source.addEventListener("frame", handleFrameEvent);
  source.addEventListener("signal", handleSignalEvent);

  source.onerror = () => {
    try {
      source.close();
    } catch (error) {
      console.error(error);
    }
    state.eventSource = null;
    if (!state.eventRetryTimer) {
      state.eventRetryTimer = setTimeout(() => {
        state.eventRetryTimer = null;
        connectPreviewEvents();
      }, 900);
    }
  };
}

function applyState(data, { hydrateForm: shouldHydrate = false } = {}) {
  state.data = data;
  hydrateChoices(data);
  if (!state.hydrated || shouldHydrate) {
    hydrateForm(data.settings, data.devices);
    state.hydrated = true;
  }

  els.heroSceneChip.textContent = data.hero.scene;
  els.heroChatChip.textContent = data.hero.chat;
  els.heroSignalChip.textContent = data.hero.signal;
  els.heroSignalStat.textContent = data.hero.signal;
  els.heroScenePill.textContent = data.hero.scene;
  els.heroChatPill.textContent = data.hero.chat;
  els.heroSignalPill.textContent = data.hero.signal;
  els.heroScenePill.hidden = !data.settings.showSceneLabel;
  els.heroSignalPill.hidden = !data.settings.showSceneRibbon;
  els.heroChatPill.hidden = data.settings.chatCompactMode;

  els.overlayShort.textContent = data.routes.overlayShort;
  els.chatShort.textContent = data.routes.chatShort;
  els.overlayRouteChip.textContent = data.routes.overlayShort;
  els.chatRouteChip.textContent = data.routes.chatShort;
  els.overlayRouteInput.value = data.routes.overlay;
  els.chatRouteInput.value = data.routes.chat;
  els.tunePlayerRouteInput.value = data.routes.musicPlayer || "";
  els.tuneQueueRouteInput.value = data.routes.musicQueue || "";
  els.tuneDockRouteInput.value = data.routes.musicDock || "";
  els.sceneSizeStat.textContent = `${data.preview.width} × ${data.preview.height}`;

  els.presetNote.textContent = data.settings.presetNote || "Пак обновлен.";
  els.captureHint.textContent = data.status.captureHint;
  els.sceneMeta.textContent = data.status.sceneMeta;
  els.chatStatusText.textContent = data.status.chat;
  els.chatPreviewStatus.textContent = data.status.chat;
  els.tuneStatusText.textContent = data.status.tune2live || "Tune2Live пока не подключен.";
  els.musicPreviewStatus.textContent = data.status.tune2live || "Tune2Live пока не подключен.";
  els.audioStatusText.textContent = data.status.audio;
  els.audioPreviewStatus.textContent = data.status.audio;
  els.audioPreviewDevice.textContent = data.devices.selected || "Не выбрано";
  els.audioPreviewThreshold.textContent = `${Math.round(data.settings.threshold)}`;
  els.audioPreviewSignal.textContent = data.hero.signal;
  els.musicDockRouteInput.value = data.routes.musicDock || "";
  els.obsHelpText.textContent = data.status.help;
  els.statusAudioLine.textContent = data.status.audio;
  els.statusChatLine.textContent = data.status.chat;
  els.statusErrorsLine.textContent = data.status.mediaErrors.length
    ? `Проблемы с файлами: ${data.status.mediaErrors.join("; ")}`
    : "Ошибок по файлам сейчас нет.";

  els.startAudioBtn.disabled = data.devices.running;
  els.stopAudioBtn.disabled = !data.devices.running;
  els.audioPreviewStartBtn.disabled = data.devices.running;
  els.audioPreviewStopBtn.disabled = !data.devices.running;
  renderMeter(data.devices.level);

  syncEmbedSource(els.chatPreviewFrame, data.routes.chat);
  syncEmbedSource(els.musicPlayerFrame, data.routes.musicPlayer);
  syncEmbedSource(els.musicQueueFrame, data.routes.musicQueue);

  if (state.frameVersion !== data.frameVersion || !state.activePreviewUrl) {
    state.frameVersion = data.frameVersion;
    queuePreviewFrame(data.sessionId, data.frameVersion);
  }
}

async function refreshState({ hydrateForm = false } = {}) {
  try {
    const data = await apiGet("/api/state");
    applyState(data, { hydrateForm });
  } catch (error) {
    console.error(error);
  }
}

async function refreshLiveState() {
  try {
    const data = await apiGet("/api/state?live=1");
    applySignalSnapshot(data);
    const nextFrameVersion = Number(data.frameVersion || 0);
    if (Number.isFinite(nextFrameVersion) && nextFrameVersion > 0) {
      if (nextFrameVersion > state.frameVersion) {
        state.frameVersion = nextFrameVersion;
      }
      queuePreviewFrame(data.sessionId, nextFrameVersion);
    }
  } catch (error) {
    console.error(error);
  }
}

function scheduleLiveRefresh(interval = 90) {
  if (state.liveRefreshTimer) {
    clearInterval(state.liveRefreshTimer);
  }
  state.liveRefreshTimer = setInterval(() => {
    refreshLiveState();
  }, interval);
}

function scheduleStateRefresh(interval = 900) {
  if (state.stateRefreshTimer) {
    clearInterval(state.stateRefreshTimer);
  }
  state.stateRefreshTimer = setInterval(() => {
    refreshState();
  }, interval);
}

function bindInputs() {
  Object.entries(fieldMap).forEach(([key, element]) => {
    if (!element) return;
    const isCheckbox = element.type === "checkbox";
    const isRange = element.type === "range";
    const eventName = isRange ? "input" : "change";
    element.addEventListener(eventName, () => {
      const value = isCheckbox ? element.checked : element.value;
      if (key === "scalePercent") els.scalePercentValue.textContent = `${Math.round(Number(value))}%`;
      if (key === "marginX") els.marginXValue.textContent = `${Math.round(Number(value))} px`;
      if (key === "marginY") els.marginYValue.textContent = `${Math.round(Number(value))} px`;
      if (key === "chatWidthPercent") els.chatWidthPercentValue.textContent = `${Math.round(Number(value))}%`;
      if (key === "threshold") els.thresholdValue.textContent = `${Math.round(Number(value))}`;
      if (key === "tuneAutoThreshold") els.tuneAutoThresholdValue.textContent = `${Math.round(Number(value))}`;
      if (key === "tuneAutoFloor") els.tuneAutoFloorValue.textContent = `${Math.round(Number(value))}%`;
      if (key === "tuneAutoReleaseMs") els.tuneAutoReleaseValue.textContent = `${(Number(value) / 1000).toFixed(1)} c`;
      scheduleWrite(key, value, isRange ? 90 : 140);
    });

    if (element.tagName === "INPUT" && !isRange && !isCheckbox && element.type !== "color") {
      element.addEventListener("blur", () => {
        scheduleWrite(key, element.value, 0);
      });
    }
  });
}

function bindViews() {
  viewButtons.forEach((button) => {
    button.addEventListener("click", () => {
      applyView(button.dataset.viewBtn || "home");
    });
  });
}

function bindButtons() {
  const bindClick = (element, handler) => {
    if (!element) return;
    element.addEventListener("click", handler);
  };

  const runAudioAction = async (path, payload = {}) => {
    try {
      const data = await apiPost(path, payload);
      applyState(data, { hydrateForm: true });
    } catch (error) {
      console.error(error);
    }
  };

  bindClick(els.openOverlayBtn, () => openUrl(state.data?.routes.overlay));
  bindClick(els.copyOverlayBtn, () => copyText(state.data?.routes.overlay));
  bindClick(els.openChatBtn, () => openUrl(state.data?.routes.chat));
  bindClick(els.copyChatBtn, () => copyText(state.data?.routes.chat));
  bindClick(els.openTuneHomeBtn, () => openUrl(state.data?.routes.tuneHome));
  bindClick(els.openTuneDashboardBtn, () => openUrl(state.data?.routes.tuneDashboard));
  bindClick(els.openTuneHomeInlineBtn, () => openUrl(state.data?.routes.tuneHome));
  bindClick(els.openTuneDashboardInlineBtn, () => openUrl(state.data?.routes.tuneDashboard));

  bindClick(els.scenePreviewOpenBtn, () => openUrl(state.data?.routes.overlay));
  bindClick(els.scenePreviewCopyBtn, () => copyText(state.data?.routes.overlay));
  bindClick(els.scenePreviewOpenChatBtn, () => openUrl(state.data?.routes.chat));
  bindClick(els.scenePreviewCopyChatBtn, () => copyText(state.data?.routes.chat));
  bindClick(els.chatPreviewOpenBtn, () => openUrl(state.data?.routes.chat));
  bindClick(els.chatPreviewCopyBtn, () => copyText(state.data?.routes.chat));
  bindClick(els.chatPreviewOpenSceneBtn, () => openUrl(state.data?.routes.overlay));
  bindClick(els.chatPreviewCopySceneBtn, () => copyText(state.data?.routes.overlay));

  bindClick(els.copyTunePlayerRouteBtn, () => copyText(state.data?.routes.musicPlayer));
  bindClick(els.openTunePlayerRouteBtn, () => openUrl(state.data?.routes.musicPlayer));
  bindClick(els.copyTunePlayerDirectBtn, () => copyText(state.data?.routes.musicPlayerDirect));
  bindClick(els.copyTuneQueueRouteBtn, () => copyText(state.data?.routes.musicQueue));
  bindClick(els.openTuneQueueRouteBtn, () => openUrl(state.data?.routes.musicQueue));
  bindClick(els.copyTuneQueueDirectBtn, () => copyText(state.data?.routes.musicQueueDirect));
  bindClick(els.copyTuneDockRouteBtn, () => copyText(state.data?.routes.musicDock));
  bindClick(els.openTuneDockRouteBtn, () => openUrl(state.data?.routes.musicDock));
  bindClick(els.openTuneDockDirectBtn, () => openUrl(state.data?.routes.musicDockDirect || state.data?.routes.tuneDashboard));

  bindClick(els.musicPreviewOpenPlayerBtn, () => openUrl(state.data?.routes.musicPlayer));
  bindClick(els.musicPreviewCopyPlayerBtn, () => copyText(state.data?.routes.musicPlayer));
  bindClick(els.musicPreviewCopyPlayerDirectBtn, () => copyText(state.data?.routes.musicPlayerDirect));
  bindClick(els.musicPreviewOpenQueueBtn, () => openUrl(state.data?.routes.musicQueue));
  bindClick(els.musicPreviewCopyQueueBtn, () => copyText(state.data?.routes.musicQueue));
  bindClick(els.musicPreviewCopyQueueDirectBtn, () => copyText(state.data?.routes.musicQueueDirect));
  bindClick(els.musicPreviewOpenDockBtn, () => openUrl(state.data?.routes.musicDock));
  bindClick(els.musicPreviewCopyDockBtn, () => copyText(state.data?.routes.musicDock));

  bindClick(els.refreshDevicesBtn, async () => {
    try {
      const data = await apiPost("/api/devices/refresh");
      applyState(data, { hydrateForm: true });
    } catch (error) {
      console.error(error);
    }
  });
  bindClick(els.audioPreviewRefreshBtn, async () => {
    try {
      const data = await apiPost("/api/devices/refresh");
      applyState(data, { hydrateForm: true });
    } catch (error) {
      console.error(error);
    }
  });

  bindClick(els.startAudioBtn, () => runAudioAction("/api/audio/start", { deviceLabel: fieldMap.deviceLabel.value }));
  bindClick(els.audioPreviewStartBtn, () => runAudioAction("/api/audio/start", { deviceLabel: fieldMap.deviceLabel.value }));
  bindClick(els.stopAudioBtn, () => runAudioAction("/api/audio/stop"));
  bindClick(els.audioPreviewStopBtn, () => runAudioAction("/api/audio/stop"));
  bindClick(els.audioPreviewOpenSceneBtn, () => openUrl(state.data?.routes.overlay));

}

async function boot() {
  ensureBars();
  bindViews();
  bindInputs();
  bindButtons();
  await refreshState({ hydrateForm: true });
  applyView(state.activeView);
  scheduleLiveRefresh(document.hidden ? 180 : 90);
  scheduleStateRefresh(document.hidden ? 1400 : 900);
  document.addEventListener("visibilitychange", () => {
    scheduleLiveRefresh(document.hidden ? 180 : 90);
    scheduleStateRefresh(document.hidden ? 1400 : 900);
    if (!document.hidden) {
      refreshLiveState();
      refreshState();
    }
  });
}

boot();
