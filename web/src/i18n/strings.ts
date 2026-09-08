export type AppLang = 'en' | 'vi'

export const STRINGS = {
  en: {
    skipToRoutes: 'Skip to route comparison',
    hero: 'Compare routes by travel time and predicted PM2.5 exposure.',
    heroSub:
      'Compare the fastest route with other feasible candidates under a time limit you choose. A lower-exposure option is not guaranteed.',
    chip: 'Pilot area · hourly data · precomputed scenarios · not live routing',
    from: 'From',
    to: 'To',
    travelMode: 'Mode',
    motorbike: 'Motorbike',
    mobility: 'Mobility (pilot)',
    walking: 'Walking',
    cycling: 'Cycling',
    ebike: 'E-bike',
    modeFootnote:
      'Cycling uses walking-speed routes in this demo pack; e-bike uses motorbike ETAs.',
    timeWindowLegend: 'Time of day (demo congestion proxy)',
    timeWindowHelp:
      'Changes the arterial traffic multiplier only. Station background stays the 06:00 field. Not a measurement of which street is jammed.',
    timeWindowLabel: (id: string) => {
      if (id === 'morning_peak') return 'Morning peak'
      if (id === 'midday') return 'Midday'
      if (id === 'evening_peak') return 'Evening peak'
      return id
    },
    gap1Link: 'Gap 1 research exhibit',
    gap1Loading: 'Loading Gap 1 exhibit…',
    gap1Empty: 'Gap 1 exhibit is not loaded yet.',
    maxTime: 'Maximum additional time',
    allowUpTo: (n: number) => `Allow up to +${n} min`,
    deltaHelp: (n: number) =>
      `Allows routes up to ${n} minutes longer than the fastest route.`,
    compare: 'Compare routes',
    comparing: 'Comparing routes…',
    howItWorks: 'How AIRPATH works',
    footnote:
      'Coordinates stay in secondary metadata (option titles and map popups). This demo does not search the live city network.',
    loadingScenarios: 'Loading demo scenarios…',
    loadingRoutes: 'Loading precomputed routes…',
    choosePair:
      'Choose a From/To pair and press Compare routes to compare travel time and predicted PM2.5 exposure.',
    bundledNote: 'Using bundled demo pack (offline / API fallback). Not live air quality.',
    liveApiNote: 'Connected to demo API.',
    langEn: 'EN',
    langVi: 'VI',
    assistTitle: 'Safety assistant (demo)',
    assistIntro:
      'Syncs turn hint + speed steps to ESP32 via BLE (or simulated JSON). Not live Google Maps — uses the selected route polyline.',
    assistOff: 'Off',
    assistDemo: 'Demo play',
    assistGps: 'GPS live',
    nextManeuver: 'Next maneuver',
    distance: 'Distance',
    targetSpeed: 'Target speed',
    resetStart: 'Reset to route start',
    pairBle: 'Pair BLE & send',
    ble: 'BLE',
    assistIdle:
      'Select a route, then enable Demo play or GPS live to preview maneuver sync for your ESP32 prototype.',
    assistDisclaimer:
      'Assistant output is a pilot demo — not medical advice, not certified navigation. Driver/rider remains responsible.',
    turnLeft: '↰ Left',
    turnRight: '↱ Right',
    turnArrive: '◎ Arrive',
    turnContinue: '↑ Continue',
    trialsTitle: 'N-run experiment log',
    trialsIntro:
      'Record each trial for the poster (assistant On vs Off). Data stays on this device until you export CSV.',
    assistantOn: 'Assistant on (C)',
    assistantOff: 'Assistant off (K)',
    speed50: 'Speed at ~50 m (km/h)',
    speedMax: 'Max speed before turn (km/h)',
    blinkerOk: 'Turn signal on time',
    yes: 'Yes',
    no: 'No',
    skip: 'Skip',
    notes: 'Notes',
    addTrial: 'Add trial',
    exportCsv: 'Export CSV',
    clearTrials: 'Clear log',
    trialsEmpty: 'No trials yet. After a demo run, add a row.',
    summaryOn: 'On (C)',
    summaryOff: 'Off (K)',
    nRuns: 'N',
    mean50: 'Mean speed ~50 m',
    pctBlinker: '% signal OK',
    pctSlow: '% ≤ 25 km/h',
    onboardingTitle: 'AIRPATH-AI demo',
    onboardingBody:
      'This app shows frozen HCMC pilot routes (hourly PM2.5 estimates) and a maneuver safety assistant for your ESP32. It is not live city routing or medical advice.',
    onboardingOk: 'Continue',
    methodologyTitle: 'How AIRPATH works',
    close: 'Close',
  },
  vi: {
    skipToRoutes: 'Nhảy tới so sánh tuyến',
    hero: 'So sánh tuyến theo thời gian đi và phơi nhiễm PM2.5 ước lượng.',
    heroSub:
      'So tuyến nhanh nhất với các phương án khả thi trong giới hạn thời gian bạn chọn. Không bảo đảm có tuyến ít phơi nhiễm hơn.',
    chip: 'Vùng pilot · dữ liệu theo giờ · kịch bản đóng băng · không định tuyến live',
    from: 'Điểm đi',
    to: 'Điểm đến',
    travelMode: 'Phương tiện',
    motorbike: 'Xe máy',
    mobility: 'Phương tiện (pilot)',
    walking: 'Đi bộ',
    cycling: 'Xe đạp',
    ebike: 'Xe điện',
    modeFootnote:
      'Xe đạp dùng ETA đi bộ trong gói demo; xe điện dùng ETA xe máy.',
    timeWindowLegend: 'Khung giờ (proxy tắc nghẽn demo)',
    timeWindowHelp:
      'Chỉ đổi hệ số tắc nghẽn động mạch. Nền trạm giữ field 06:00. Không đo tắc thực tế từng đường.',
    timeWindowLabel: (id: string) => {
      if (id === 'morning_peak') return 'Giờ cao điểm sáng'
      if (id === 'midday') return 'Trưa'
      if (id === 'evening_peak') return 'Chiều tối'
      return id
    },
    gap1Link: 'Triển lãm nghiên cứu Gap 1',
    gap1Loading: 'Đang tải triển lãm Gap 1…',
    gap1Empty: 'Triển lãm Gap 1 chưa được tải.',
    maxTime: 'Thời gian thêm tối đa',
    allowUpTo: (n: number) => `Cho phép thêm tối đa +${n} phút`,
    deltaHelp: (n: number) =>
      `Cho phép tuyến dài hơn tuyến nhanh nhất tới ${n} phút.`,
    compare: 'So sánh tuyến',
    comparing: 'Đang so sánh…',
    howItWorks: 'AIRPATH hoạt động thế nào',
    footnote:
      'Tọa độ nằm ở metadata phụ. Demo không tìm kiếm mạng lưới thành phố live.',
    loadingScenarios: 'Đang tải kịch bản demo…',
    loadingRoutes: 'Đang tải tuyến đã tính sẵn…',
    choosePair:
      'Chọn điểm đi/đến rồi nhấn So sánh tuyến để xem thời gian và phơi nhiễm PM2.5 ước lượng.',
    bundledNote: 'Đang dùng gói demo đóng trong app (offline / API lỗi). Không phải không khí realtime.',
    liveApiNote: 'Đã kết nối API demo.',
    langEn: 'EN',
    langVi: 'VI',
    assistTitle: 'Trợ lý an toàn (demo)',
    assistIntro:
      'Đồng bộ hướng rẽ + bậc tốc độ tới ESP32 qua BLE (hoặc JSON mô phỏng). Không phải Google Maps live — dùng polyline tuyến đã chọn.',
    assistOff: 'Tắt',
    assistDemo: 'Chạy demo',
    assistGps: 'GPS thật',
    nextManeuver: 'Maneuver tiếp',
    distance: 'Khoảng cách',
    targetSpeed: 'Tốc độ mục tiêu',
    resetStart: 'Về đầu tuyến',
    pairBle: 'Ghép BLE & gửi',
    ble: 'BLE',
    assistIdle:
      'Chọn tuyến, bật Chạy demo hoặc GPS thật để xem đồng bộ maneuver cho ESP32.',
    assistDisclaimer:
      'Đầu ra trợ lý là demo pilot — không phải tư vấn y tế, không thay thế dẫn đường chứng nhận. Người điều khiển chịu trách nhiệm.',
    turnLeft: '↰ Trái',
    turnRight: '↱ Phải',
    turnArrive: '◎ Đến nơi',
    turnContinue: '↑ Đi tiếp',
    trialsTitle: 'Nhật ký thí nghiệm N lượt',
    trialsIntro:
      'Ghi từng lượt cho poster (có/không trợ lý). Dữ liệu lưu trên máy cho tới khi xuất CSV.',
    assistantOn: 'Có trợ lý (C)',
    assistantOff: 'Không trợ lý (K)',
    speed50: 'Tốc độ ~50 m (km/h)',
    speedMax: 'Tốc độ max trước rẽ (km/h)',
    blinkerOk: 'Xi-nhan đúng lúc',
    yes: 'Có',
    no: 'Không',
    skip: 'Bỏ qua',
    notes: 'Ghi chú',
    addTrial: 'Thêm lượt',
    exportCsv: 'Xuất CSV',
    clearTrials: 'Xóa nhật ký',
    trialsEmpty: 'Chưa có lượt nào. Sau khi chạy demo, thêm một dòng.',
    summaryOn: 'Có (C)',
    summaryOff: 'Không (K)',
    nRuns: 'N',
    mean50: 'TB tốc độ ~50 m',
    pctBlinker: '% xi-nhan OK',
    pctSlow: '% ≤ 25 km/h',
    onboardingTitle: 'Demo AIRPATH-AI',
    onboardingBody:
      'App hiển thị tuyến pilot HCMC đã đóng băng (PM2.5 ước lượng theo giờ) và trợ lý an toàn maneuver cho ESP32. Không phải định tuyến live hay tư vấn y tế.',
    onboardingOk: 'Tiếp tục',
    methodologyTitle: 'AIRPATH hoạt động thế nào',
    close: 'Đóng',
  },
} as const
