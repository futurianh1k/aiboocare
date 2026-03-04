# 프론트엔드 정책 관리 콘솔 구현

## 날짜
2026-03-04

## 요청 내용
`docs/아이부다마고치.txt` 파일의 화면설계(6308라인 이후)를 기반으로 프론트엔드 운영 콘솔 구현

## 구현 내용

### 1. 디자인 토큰 업데이트 (`index.css`)
문서에 정의된 디자인 토큰을 CSS 변수로 구현:
- **Color Tokens**: Gray scale, Primary (Indigo), Success, Warning, Error, Info
- **Typography**: Inter (primary), JetBrains Mono (mono)
- **Spacing Scale**: 4px ~ 48px
- **Border Radius**: sm, md, lg, xl, 2xl, full
- **Shadows**: sm, md, lg, xl
- **Layout Variables**: sidebar-width (240px), header-height (56px), drawer-width (420px)

### 2. 레이아웃 구조 (`Layout.tsx`)
문서 기반 3단 레이아웃:
- **Left Sidebar (240px)**: 로고, Tenant Switcher, 네비게이션, 사용자 정보
- **Top Header (56px)**: Breadcrumbs, Global Search, User menu
- **Main Content Area**: 페이지별 콘텐츠

### 3. 네비게이션 메뉴 구조
```
모니터링
├── 대시보드
├── 돌봄 대상자
├── 케이스 관리
└── 디바이스

정책 관리
├── Bundles
├── Thresholds
├── Call Tree
└── Rules

도구
├── Simulator
└── Audit
```

### 4. 구현된 페이지들

#### 4.1 Bundles 페이지 (`/bundles`)
- **목록 테이블**: Name, Version, Status, Effective From, Updated, Actions
- **필터**: Status (Draft/Active/Archived), Name search
- **상세 패널**: Bundle Summary, Quick Health, Scope Coverage, Quick Actions
- **액션**: Create Draft, Clone Active, Validate, Publish, Rollback

#### 4.2 Thresholds 페이지 (`/thresholds`)
- **카탈로그 테이블**: Key, Domain, Metric, Condition, Duration/Occ, Severity, Enabled
- **필터**: Domain, Severity, Enabled, Search
- **우측 Drawer 편집 패널**:
  - Identity (key, domain, metric)
  - Condition (operator, value)
  - Aggregation (duration_sec, occurrences)
  - Outcome (severity, enabled)
  - Inline validation panel

#### 4.3 Call Tree 페이지 (`/calltree`)
- **플랜 목록**: Name, Event Group, Min Severity, Cooldown, Enabled
- **플랜 에디터**:
  - Plan Settings (name, group, severity, cooldown)
  - Stages (드래그 정렬, 채널 선택)
  - Target types: guardian1, guardian2, caregiver, operations, ems (119)
  - Channels: push, sms, voice, email

#### 4.4 Rules 페이지 (`/rules`)
- **규칙 테이블**: Key, Domain, Priority, Scope, Description, Enabled
- **필터**: Domain (EMS/VERIFY/ESCALATION/VOICE), Scope (edge/cloud/both)
- **편집 Drawer**:
  - Rule meta (key, domain, priority, scope)
  - Builder/JSON 모드 토글
  - Condition builder (AND/OR 트리)
  - Action builder
  - Reference checks

#### 4.5 Simulator 페이지 (`/simulator`)
- **입력 패널**:
  - Target Scope (Tenant 전체/특정 User/특정 Device)
  - Period (1h/24h/7d, datetime picker)
  - Policy Bundle 선택 (Compare mode)
- **결과 패널**:
  - KPI: Total Alerts, Critical, 119 Escalations, Storm Risk
  - Charts: By Event Group, By Severity, Escalation Funnel
  - Top Triggers 테이블
  - Timeline (Hourly Distribution)
  - Findings (경고/권장사항)

#### 4.6 Audit 페이지 (`/audit`)
- **필터**: Date range, Actor, Action, Resource type, Search
- **로그 테이블**: Timestamp, Actor, Action, Resource, Resource ID, Detail
- **상세 Drawer**:
  - Basic Info (timestamp, actor, role, action, resource)
  - Detail description
  - Diff View (before/after JSON)
  - Raw Data

### 5. 공통 컴포넌트
- **Button variants**: primary, secondary, danger, ghost, sm, lg
- **Badge variants**: gray, primary, success, warning, error, info
- **Form elements**: input, select, textarea, checkbox, toggle
- **Card**: header, body
- **Drawer**: overlay, header, body, footer
- **Table**: responsive, hover states
- **Tabs**: active state with border indicator

## 기술 스택
- React 18 + TypeScript
- Vite (빌드 도구)
- React Router (라우팅)
- TanStack Query (API 상태 관리)
- Recharts (차트)
- Lucide React (아이콘)
- date-fns (날짜 포맷팅)
- Vanilla CSS with CSS Variables (디자인 토큰)

## 참고 자료
- 원본 문서: `docs/아이부다마고치.txt` (6308라인 이후)
- 화면 설계 섹션: 운영 콘솔 IA, 와이어프레임, 디자인 토큰

## 테스트 방법
```bash
cd frontend
npm run dev
# http://localhost:3000 접속
# 테스트 계정: admin / admin
```
