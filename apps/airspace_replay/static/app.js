const state = {
  events: [],
  cursor: 0,
  timer: null,
  active: new Map(),
  selectedObjectId: null,
};

const els = {
  runSelect: document.querySelector("#runSelect"),
  fromInput: document.querySelector("#fromInput"),
  toInput: document.querySelector("#toInput"),
  limitInput: document.querySelector("#limitInput"),
  trackPointsInput: document.querySelector("#trackPointsInput"),
  speedSelect: document.querySelector("#speedSelect"),
  loadBtn: document.querySelector("#loadBtn"),
  playBtn: document.querySelector("#playBtn"),
  resetBtn: document.querySelector("#resetBtn"),
  fitBtn: document.querySelector("#fitBtn"),
  timeline: document.querySelector("#timeline"),
  clock: document.querySelector("#clock"),
  eventCount: document.querySelector("#eventCount"),
  activeCount: document.querySelector("#activeCount"),
  objectDetails: document.querySelector("#objectDetails"),
  status: document.querySelector("#status"),
};

const map = L.map("map", {
  preferCanvas: true,
  zoomControl: false,
  zoomSnap: 0.25,
  wheelPxPerZoomLevel: 80,
}).setView([53.9, 27.6], 4);

L.control.zoom({ position: "bottomleft" }).addTo(map);
L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19,
  maxNativeZoom: 19,
  detectRetina: true,
  attribution: "&copy; OpenStreetMap",
}).addTo(map);

function colorFor(event) {
  const value = event.truth_affiliation || "neutral";
  if (value === "adversary") return "#b5352f";
  if (value === "friendly") return "#26734d";
  if (value === "civilian") return "#2578b5";
  return "#8a8f37";
}

function setStatus(message) {
  els.status.textContent = message;
}

function toDatetimeLocal(value) {
  if (!value) return "";
  return value.replace(" ", "T").replace("Z", "").slice(0, 19);
}

function inputToIso(value) {
  if (!value) return "";
  return `${value}Z`;
}

function trackPointLimit() {
  const raw = Number(els.trackPointsInput.value);
  if (!Number.isFinite(raw)) return 25;
  return Math.max(1, Math.min(500, Math.floor(raw)));
}

async function fetchJson(url) {
  const res = await fetch(url);
  const payload = await res.json();
  if (!res.ok) {
    throw new Error(payload.error || `HTTP ${res.status}`);
  }
  return payload;
}

async function loadRuns() {
  const payload = await fetchJson("/api/runs?limit=100");
  els.runSelect.innerHTML = "";

  for (const run of payload.runs) {
    const option = document.createElement("option");
    option.value = run.run_id;
    option.textContent = `${run.run_id.slice(0, 8)} | ${run.objects} objects | ${run.events} events`;
    option.dataset.from = run.min_event_time;
    option.dataset.to = run.max_event_time;
    els.runSelect.append(option);
  }

  if (payload.runs.length > 0) {
    applySelectedRunWindow();
    setStatus(`Loaded ${payload.runs.length} runs`);
  } else {
    setStatus("No runs found in ClickHouse");
  }
}

function applySelectedRunWindow() {
  const selected = els.runSelect.selectedOptions[0];
  if (!selected) return;
  els.fromInput.value = toDatetimeLocal(selected.dataset.from);
  els.toInput.value = toDatetimeLocal(selected.dataset.to);
}

async function loadReplay() {
  stopReplay();
  clearMap();
  setStatus("Loading replay window...");

  const params = new URLSearchParams({
    run_id: els.runSelect.value,
    from: inputToIso(els.fromInput.value),
    to: inputToIso(els.toInput.value),
    limit: els.limitInput.value || "50000",
  });
  const payload = await fetchJson(`/api/replay?${params.toString()}`);
  state.events = payload.events;
  state.cursor = 0;
  els.timeline.max = Math.max(0, state.events.length - 1);
  els.timeline.value = 0;
  els.timeline.disabled = state.events.length === 0;
  els.playBtn.disabled = state.events.length === 0;
  els.resetBtn.disabled = state.events.length === 0;
  els.fitBtn.disabled = state.events.length === 0;
  els.eventCount.textContent = String(state.events.length);
  setStatus(`Replay loaded: ${state.events.length} events`);

  if (state.events.length > 0) {
    stepTo(0);
    fitLoadedWindow();
  }
}

function clearMap() {
  for (const item of state.active.values()) {
    map.removeLayer(item.marker);
    map.removeLayer(item.track);
  }
  state.active.clear();
  state.selectedObjectId = null;
  els.objectDetails.textContent = "No object selected";
  els.activeCount.textContent = "0";
  els.clock.textContent = "-";
}

function resetReplay() {
  stopReplay();
  clearMap();
  state.cursor = 0;
  els.timeline.value = 0;
  if (state.events.length > 0) {
    stepTo(0);
  }
}

function stepTo(index) {
  clearMap();
  const target = Math.max(0, Math.min(index, state.events.length - 1));
  for (let i = 0; i <= target; i += 1) {
    applyEvent(state.events[i], false);
  }
  state.cursor = target;
  els.timeline.value = target;
  updateStats();
}

function applyNextBatch() {
  if (state.cursor >= state.events.length - 1) {
    stopReplay();
    return;
  }

  const speed = Number(els.speedSelect.value);
  const batchSize = Math.max(1, Math.ceil(speed));
  for (let i = 0; i < batchSize && state.cursor < state.events.length - 1; i += 1) {
    state.cursor += 1;
    applyEvent(state.events[state.cursor], true);
  }
  els.timeline.value = state.cursor;
  updateStats();
}

function applyEvent(event, fitOnFirst) {
  if (!event) return;

  if (event.event_type === "despawned") {
    const existing = state.active.get(event.object_id);
    if (existing) {
      map.removeLayer(existing.marker);
      map.removeLayer(existing.track);
      state.active.delete(event.object_id);
    }
    return;
  }

  if (event.lat == null || event.lon == null) return;

  const latLng = [Number(event.lat), Number(event.lon)];
  const color = colorFor(event);
  let item = state.active.get(event.object_id);

  if (!item) {
    const marker = L.circleMarker(latLng, {
      radius: 6,
      color,
      fillColor: color,
      fillOpacity: 0.85,
      weight: 2,
    }).addTo(map);
    marker.on("click", () => selectObject(event.object_id, true));

    const track = L.polyline([latLng], {
      color,
      weight: 3,
      opacity: 0.72,
    }).addTo(map);

    item = { marker, track, lastEvent: event, trail: [latLng] };
    state.active.set(event.object_id, item);

    if (fitOnFirst && state.active.size === 1) {
      map.setView(latLng, 6);
    }
  } else {
    item.marker.setLatLng(latLng);
    item.marker.setStyle({ color, fillColor: color });
    item.lastEvent = event;
    item.trail.push(latLng);
    item.trail = item.trail.slice(-trackPointLimit());
    item.track.setLatLngs(item.trail);
    item.track.setStyle({ color });
  }

  if (state.selectedObjectId === event.object_id) {
    renderObjectDetails(event);
  }
}

function selectObject(objectId, focus = false) {
  state.selectedObjectId = objectId;
  const item = state.active.get(objectId);
  if (item) {
    renderObjectDetails(item.lastEvent);
    if (focus) {
      map.setView(item.marker.getLatLng(), Math.max(map.getZoom(), 13), {
        animate: true,
      });
    }
  }
}

function renderObjectDetails(event) {
  els.objectDetails.textContent = JSON.stringify({
    object_id: event.object_id,
    callsign: event.callsign,
    event_time: event.event_time,
    platform_class: event.platform_class,
    scenario_bucket: event.scenario_bucket,
    mission_profile: event.mission_profile,
    affiliation: event.truth_affiliation,
    altitude: event.altitude,
    speed: event.speed,
    heading: event.heading,
  }, null, 2);
}

function updateStats() {
  const event = state.events[state.cursor];
  els.clock.textContent = event ? event.event_time.replace("T", " ").replace("Z", "") : "-";
  els.activeCount.textContent = String(state.active.size);
}

function fitLoadedWindow() {
  const points = [];
  const sampleStep = Math.max(1, Math.floor(state.events.length / 2500));
  for (let i = 0; i < state.events.length; i += sampleStep) {
    const event = state.events[i];
    if (event.lat != null && event.lon != null) {
      points.push([Number(event.lat), Number(event.lon)]);
    }
  }
  if (points.length === 0) return;

  const bounds = L.latLngBounds(points);
  if (bounds.isValid()) {
    map.fitBounds(bounds, {
      padding: [32, 32],
      maxZoom: 10,
    });
  }
}

function fitActiveObjects() {
  const points = Array.from(state.active.values()).map((item) => item.marker.getLatLng());
  if (points.length === 0) {
    fitLoadedWindow();
    return;
  }

  if (points.length === 1) {
    map.setView(points[0], Math.max(map.getZoom(), 13), {
      animate: true,
    });
    return;
  }

  const bounds = L.latLngBounds(points);
  if (bounds.isValid()) {
    map.fitBounds(bounds, {
      padding: [48, 48],
      maxZoom: 11,
      animate: true,
    });
  }
}

function playReplay() {
  if (state.timer) {
    stopReplay();
    return;
  }
  els.playBtn.textContent = "Pause";
  state.timer = setInterval(applyNextBatch, 120);
}

function stopReplay() {
  if (state.timer) {
    clearInterval(state.timer);
    state.timer = null;
  }
  els.playBtn.textContent = "Play";
}

els.runSelect.addEventListener("change", applySelectedRunWindow);
els.loadBtn.addEventListener("click", () => loadReplay().catch((err) => setStatus(err.message)));
els.playBtn.addEventListener("click", playReplay);
els.resetBtn.addEventListener("click", resetReplay);
els.fitBtn.addEventListener("click", fitActiveObjects);
els.timeline.addEventListener("input", () => stepTo(Number(els.timeline.value)));
els.trackPointsInput.addEventListener("change", () => stepTo(state.cursor));

loadRuns().catch((err) => setStatus(err.message));
