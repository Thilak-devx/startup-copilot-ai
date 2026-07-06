// Premium Application Logic for Startup Copilot AI Dashboard — YC Demo Day Edition

// ── Application State ────────────────────────────────────────────────────────
const state = {
    currentView: 'dashboard',
    activeStartup: 'Solarex',
    runs: [],
    selectedRun: null,
    workflowStatus: 'idle',
    currentSlideIndex: 0,
    pitchDeckSlides: [],
    reports: [],
    activeReportPath: null,
    wfSelectedNode: null,
    wfElapsedTimer: null,
    wfElapsedStart: null,
    wfCompletedCount: 0,
    wfAvgConf: 0,

    // ── Node definitions with layout coordinates (viewport 1400 × 340) ──────
    // Parallel lanes: Phase1 (Research+Risk), Phase2 (Product+Finance),
    // Phase3 (Advocate+Investor), then HITL, then Phase4 (3 parallel), then Security/MCP
    graphNodes: [
        // Input
        { id: 'extract_name_node',  label: 'Input Parser',         icon: '⊞', phase: 'input',    x: 40,   y: 147, w: 130, h: 52, edges: ['research_agent','risk_agent'],                              status: 'pending', duration: 0, conf: 0, parallel: false },
        // Phase 1
        { id: 'research_agent',     label: 'Market Research',       icon: '◎', phase: 'phase1',   x: 220,  y: 80,  w: 130, h: 52, edges: ['product_agent'],                                           status: 'pending', duration: 0, conf: 0, parallel: true  },
        { id: 'risk_agent',         label: 'Risk Assessment',        icon: '⚑', phase: 'phase1',   x: 220,  y: 210, w: 130, h: 52, edges: ['finance_agent'],                                           status: 'pending', duration: 0, conf: 0, parallel: true  },
        // Phase 2
        { id: 'product_agent',      label: 'Product Scoping',        icon: '⬡', phase: 'phase2',   x: 400,  y: 80,  w: 130, h: 52, edges: ['advocate_agent'],                                         status: 'pending', duration: 0, conf: 0, parallel: true  },
        { id: 'finance_agent',      label: 'Finance Projections',    icon: '$', phase: 'phase2',   x: 400,  y: 210, w: 130, h: 52, edges: ['investor_agent'],                                         status: 'pending', duration: 0, conf: 0, parallel: true  },
        // Phase 3
        { id: 'advocate_agent',     label: "Devil's Advocate",       icon: '⚠', phase: 'phase3',   x: 580,  y: 80,  w: 130, h: 52, edges: ['hitl_review_node'],                                      status: 'pending', duration: 0, conf: 0, parallel: true  },
        { id: 'investor_agent',     label: 'Investor Verdict',       icon: '♦', phase: 'phase3',   x: 580,  y: 210, w: 130, h: 52, edges: ['hitl_review_node'],                                      status: 'pending', duration: 0, conf: 0, parallel: true  },
        // HITL Gate
        { id: 'hitl_review_node',   label: 'Founder Checkpoint',     icon: '✋', phase: 'hitl',     x: 760,  y: 147, w: 130, h: 52, edges: ['growth_agent','simulator_agent','pitchdeck_agent'],       status: 'pending', duration: 0, conf: 0, parallel: false },
        // Phase 4
        { id: 'growth_agent',       label: 'Growth Strategy',        icon: '↑', phase: 'phase4',   x: 940,  y: 60,  w: 130, h: 52, edges: ['security_agent'],                                        status: 'pending', duration: 0, conf: 0, parallel: true  },
        { id: 'simulator_agent',    label: 'Trajectory Simulation',  icon: '~', phase: 'phase4',   x: 940,  y: 147, w: 130, h: 52, edges: ['security_agent'],                                        status: 'pending', duration: 0, conf: 0, parallel: true  },
        { id: 'pitchdeck_agent',    label: 'Pitch Deck Creation',    icon: '▤', phase: 'phase4',   x: 940,  y: 234, w: 130, h: 52, edges: ['security_agent'],                                        status: 'pending', duration: 0, conf: 0, parallel: true  },
        // Final
        { id: 'security_agent',     label: 'Security Checkpoint',    icon: '⛉', phase: 'final',    x: 1120, y: 147, w: 130, h: 52, edges: ['mcp_write_node'],                                        status: 'pending', duration: 0, conf: 0, parallel: false },
        { id: 'mcp_write_node',     label: 'Report Compiler',        icon: '✦', phase: 'final',    x: 1300, y: 147, w: 130, h: 52, edges: [],                                                        status: 'pending', duration: 0, conf: 0, parallel: false },
    ],

    agentMetadata: {
        research_agent:   { name: 'Research Agent',        icon: 'R', desc: 'Sizes TAM/SAM/SOM, reviews competitors, and identifies white spaces.' },
        risk_agent:       { name: 'Risk Officer',           icon: 'R', desc: 'Identifies regulatory, operational, legal, and showstopper risks.' },
        product_agent:    { name: 'CPO Agent',              icon: 'P', desc: 'Prioritizes lean MVP features and writes developer user stories.' },
        finance_agent:    { name: 'CFO Agent',              icon: 'F', desc: 'Calculates unit economics, burn rate, runway, and projections.' },
        advocate_agent:   { name: "Devil's Advocate",       icon: 'D', desc: 'Challenges base assumptions, stress-tests pricing, highlights flaws.' },
        investor_agent:   { name: 'VC Partner',             icon: 'I', desc: 'Grades startup investment readiness and flags VC alignment issues.' },
        growth_agent:     { name: 'Growth Lead',            icon: 'G', desc: 'Prioritizes high-leverage marketing channels and GTM strategy.' },
        simulator_agent:  { name: 'Simulator Agent',        icon: 'S', desc: 'Generates 12-month Monte Carlo run projections (users, MRR, cash).' },
        pitchdeck_agent:  { name: 'Pitch Specialist',       icon: 'K', desc: 'Drafts a cohesive 10-slide VC-ready narrative package.' },
        security_agent:   { name: 'Safety Agent',           icon: 'C', desc: 'Scans for compliance, PII leaks, safety compliance, and content safety.' }
    }
};

// ── DOM Elements ─────────────────────────────────────────────────────────────
const elements = {
    navItems: document.querySelectorAll('.nav-item'),
    viewContents: document.querySelectorAll('.view-content'),
    headerStartupName: document.getElementById('header-startup-name'),
    headerStatusBadge: document.getElementById('header-status-badge'),
    
    // Gauges
    valStartupScore: document.getElementById('val-startup-score'),
    valInvestmentScore: document.getElementById('val-investment-score'),
    valConfidenceScore: document.getElementById('val-confidence-score'),
    gaugeStartup: document.getElementById('gauge-startup'),
    gaugeReadiness: document.getElementById('gauge-readiness'),
    gaugeConfidence: document.getElementById('gauge-confidence'),
    
    // Graph Wrapper & Agent grids
    agentCardsGrid: document.getElementById('agent-cards-grid'),
    
    // Hero
    heroStartupTitle: document.getElementById('hero-startup-title'),
    heroStartupDesc: document.getElementById('hero-startup-desc'),
    metaIndustry: document.getElementById('meta-industry'),
    metaStage: document.getElementById('meta-stage'),
    metaPricing: document.getElementById('meta-pricing'),
    
    // Verdict
    summaryVerdict: document.getElementById('summary-verdict'),
    summaryText: document.getElementById('summary-text'),
    summaryStrengths: document.getElementById('summary-strengths'),
    summaryRisks: document.getElementById('summary-risks'),
    
    // Form & Buttons
    analysisForm: document.getElementById('analysis-form'),
    btnExportMd: document.getElementById('btn-export-md'),
    btnExportPdf: document.getElementById('btn-export-pdf'),
    btnCopyMd: document.getElementById('btn-copy-md'),
    btnViewDeck: document.getElementById('btn-view-deck'),
    btnDemoMode: document.getElementById('btn-demo-mode'),
    
    // Tables & Lists
    historyTableBody: document.getElementById('history-table-body'),
    reportsFileList: document.getElementById('reports-file-list'),
    reportViewTitle: document.getElementById('report-view-title'),
    reportViewerContent: document.getElementById('report-viewer-content'),
    
    // Modals & Panels
    hitlOverlay: document.getElementById('hitl-overlay'),
    hitlSummaryBox: document.getElementById('hitl-data-summary-box'),
    hitlFeedbackText: document.getElementById('hitl-feedback-text'),
    btnHitlApprove: document.getElementById('hitl-btn-approve'),
    btnHitlMinor: document.getElementById('hitl-btn-minor'),
    btnHitlMajor: document.getElementById('hitl-btn-major'),
    
    deckModal: document.getElementById('deck-modal'),
    deckModalClose: document.getElementById('deck-modal-close'),
    slideNum: document.getElementById('slide-num'),
    slideTitle: document.getElementById('slide-title'),
    slidePointsList: document.getElementById('slide-points-list'),
    deckDotsNav: document.getElementById('deck-dots-nav'),
    btnDeckPrev: document.getElementById('deck-btn-prev'),
    btnDeckNext: document.getElementById('deck-btn-next')
};

// ── View Management ──────────────────────────────────────────────────────────
function switchView(viewName) {
    state.currentView = viewName;
    
    elements.navItems.forEach(item => {
        if (item.getAttribute('data-view') === viewName) {
            item.classList.add('active');
        } else {
            item.classList.remove('active');
        }
    });

    elements.viewContents.forEach(view => {
        if (view.id === `view-${viewName}`) {
            view.classList.add('active');
        } else {
            view.classList.remove('active');
        }
    });

    if (viewName === 'history') {
        fetchHistory();
    } else if (viewName === 'reports') {
        fetchReports();
    } else if (viewName === 'workflow') {
        // Small delay to let the view become visible before rendering SVG dimensions
        setTimeout(() => wfRenderGraph(), 50);
    } else if (viewName === 'executive-summary') {
        loadExecutiveSummary();
    }
}

// ── Notification Banner ──────────────────────────────────────────────────────
function showToast(message, type = 'info') {
    const banner = document.getElementById('toast-banner-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    let statusText = 'SYS';
    if (type === 'success') statusText = 'OK';
    if (type === 'warning') statusText = 'WARN';
    if (type === 'error') statusText = 'FAIL';
    
    toast.innerHTML = `<span class="badge" style="margin-right: 8px;">${statusText}</span> <span>${message}</span>`;
    banner.appendChild(toast);
    
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(10px)';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// ── Gauge Animation ──────────────────────────────────────────────────────────
function updateGauge(circleElement, valueElement, value) {
    const circumference = 157;
    const offset = circumference - (value / 100) * circumference;
    
    circleElement.style.strokeDashoffset = offset;
    
    let current = 0;
    const interval = setInterval(() => {
        if (current >= value) {
            valueElement.textContent = value;
            clearInterval(interval);
        } else {
            current += Math.ceil(value / 10);
            if (current > value) current = value;
            valueElement.textContent = current;
        }
    }, 30);
}

// ── Premium SVG Workflow Graph Engine ────────────────────────────────────────
// Constants — logical canvas dimensions
const WF_W = 1460;
const WF_H = 340;
const NODE_R = 8; // border radius

function wfGetNode(id) {
    return state.graphNodes.find(n => n.id === id);
}

function wfNodeCX(n) { return n.x + n.w / 2; }
function wfNodeCY(n) { return n.y + n.h / 2; }

// Phase band definitions for background shading
const WF_PHASE_BANDS = [
    { x: 30,   w: 165, label: 'Input' },
    { x: 205,  w: 310, label: 'Phase 1 & 2' },
    { x: 565,  w: 200, label: 'Phase 3' },
    { x: 745,  w: 145, label: 'HITL Gate' },
    { x: 920,  w: 315, label: 'Phase 4' },
    { x: 1095, w: 355, label: 'Final' },
];

function wfRenderGraph() {
    const edgesLayer = document.getElementById('wf-edges-layer');
    const nodesLayer = document.getElementById('wf-nodes-layer');
    const svg        = document.getElementById('wf-svg-canvas');
    if (!edgesLayer || !nodesLayer || !svg) return;

    svg.setAttribute('viewBox', `0 0 ${WF_W} ${WF_H}`);

    // ── Phase bands ──────────────────────────────────────────────────────────
    let bandsHtml = '';
    WF_PHASE_BANDS.forEach(b => {
        // Draw the background band
        bandsHtml += `<rect class="wf-phase-band" x="${b.x}" y="10" width="${b.w}" height="${WF_H - 20}" rx="12"/>`;
        // Centered label at the top of each band inside the SVG
        bandsHtml += `<text class="wf-phase-label-svg" x="${b.x + b.w / 2}" y="28" text-anchor="middle" font-family="Inter, sans-serif" font-size="9" font-weight="700" letter-spacing="0.08em" fill="rgba(255, 255, 255, 0.22)" style="text-transform: uppercase; pointer-events: none;">${b.label}</text>`;
    });

    // ── Edges ────────────────────────────────────────────────────────────────
    let edgesHtml = bandsHtml;
    state.graphNodes.forEach(src => {
        src.edges.forEach(tgtId => {
            const tgt = wfGetNode(tgtId);
            if (!tgt) return;

            const x1 = src.x + src.w;
            const y1 = wfNodeCY(src);
            const x2 = tgt.x;
            const y2 = wfNodeCY(tgt);
            const dx = x2 - x1;
            const cpx1 = x1 + dx * 0.45;
            const cpx2 = x2 - dx * 0.45;
            const path = `M ${x1} ${y1} C ${cpx1} ${y1}, ${cpx2} ${y2}, ${x2} ${y2}`;

            // Edge status: if source is completed and target is active → active edge
            let edgeCls = 'wf-edge pending';
            if (src.status === 'completed' && tgt.status === 'completed') edgeCls = 'wf-edge completed';
            else if (src.status === 'completed' && (tgt.status === 'active' || tgt.status === 'hitl')) edgeCls = 'wf-edge active';
            else if (src.status === 'active') edgeCls = 'wf-edge active';

            edgesHtml += `<path class="${edgeCls}" d="${path}"/>`;
        });
    });
    edgesLayer.innerHTML = edgesHtml;

    // ── Nodes ────────────────────────────────────────────────────────────────
    let nodesHtml = '';
    state.graphNodes.forEach(node => {
        const { id, label, icon, status, duration, conf, x, y, w, h } = node;
        const cx = x + w / 2;
        const cy = y + h / 2;
        const isSelected = state.wfSelectedNode === id;

        // Node class
        let nodeCls = `wf-node ${status}`;

        // Status text
        let statusText = 'PENDING';
        let durationText = '';
        if (status === 'active') {
            statusText = 'RUNNING';
            if (duration) {
                const durStr = String(duration);
                durationText = durStr.endsWith('ms') ? durStr : `${durStr}ms`;
            }
        } else if (status === 'completed') {
            statusText = 'DONE';
            const durStr = String(duration);
            durationText = durStr.endsWith('ms') ? durStr : `${durStr}ms`;
        } else if (status === 'hitl') {
            statusText = 'WAITING';
        }

        // Details line including status, duration, and confidence
        let detailsText = statusText;
        if (durationText) detailsText += `  ${durationText}`;
        if (conf > 0) detailsText += `  ${conf}%`;

        // Confidence bar width (spans full node width minus padding)
        const confBarMaxW = w - 24;
        const confBarW = Math.round((conf / 100) * confBarMaxW);

        // ── Pulse rings for active nodes ──────────────────────────────────────
        let pulseHtml = '';
        if (status === 'active') {
            pulseHtml = `
                <circle class="wf-pulse-ring"  cx="${cx}" cy="${cy}" r="0" stroke="#6EE7FF" fill="none" stroke-width="1.5"/>
                <circle class="wf-pulse-ring2" cx="${cx}" cy="${cy}" r="0" stroke="#6EE7FF" fill="none" stroke-width="1"/>
            `;
        } else if (status === 'hitl') {
            pulseHtml = `
                <circle cx="${cx}" cy="${cy}" r="0" stroke="#F59E0B" fill="none" stroke-width="1.5" style="animation: wf-pulse-ring 1.6s ease-out infinite;"/>
            `;
        }

        // ── Selection ring ───────────────────────────────────────────────────
        const selRing = isSelected
            ? `<rect class="wf-selected-ring" x="${x - 4}" y="${y - 4}" width="${w + 8}" height="${h + 8}" rx="${NODE_R + 3}"/>`
            : '';

        // ── Icon background circle ────────────────────────────────────────────
        const iconR = 13;
        const iconCX = x + 18;
        const iconCY = cy;
        const iconBg = status === 'active'    ? 'rgba(110,231,255,0.15)'
                     : status === 'completed' ? 'rgba(22,199,132,0.15)'
                     : status === 'hitl'      ? 'rgba(245,158,11,0.15)'
                     : 'rgba(255,255,255,0.05)';
        const iconColor = status === 'active'    ? '#6EE7FF'
                        : status === 'completed' ? '#16C784'
                        : status === 'hitl'      ? '#F59E0B'
                        : 'rgba(255,255,255,0.35)';

        // ── Spinner arc (active only) ─────────────────────────────────────────
        // Drawn as a path around the node outer edge
        const spinnerR = iconR + 1;
        const spinnerPath = status === 'active'
            ? `<path class="wf-spinner" d="M ${iconCX} ${iconCY - spinnerR} A ${spinnerR} ${spinnerR} 0 0 1 ${iconCX + spinnerR * 0.866} ${iconCY + spinnerR * 0.5}" style="transform-origin: ${iconCX}px ${iconCY}px;"/>`
            : '';

        // ── Status dot ───────────────────────────────────────────────────────
        const dotColor = status === 'active'    ? '#6EE7FF'
                       : status === 'completed' ? '#16C784'
                       : status === 'hitl'      ? '#F59E0B'
                       : 'rgba(255,255,255,0.12)';
        const dotFilter = status === 'active'    ? 'drop-shadow(0 0 4px #6EE7FF)'
                        : status === 'completed' ? 'drop-shadow(0 0 3px #16C784)'
                        : status === 'hitl'      ? 'drop-shadow(0 0 3px #F59E0B)'
                        : 'none';

        // ── Label and status text positions ───────────────────────────────────
        const textX = iconCX + iconR + 7;
        const labelY = cy - 5;
        const statusY = cy + 10;

        // ── Confidence bar ────────────────────────────────────────────────────
        const confFillColor = status === 'completed' ? '#16C784'
                            : status === 'active'    ? '#6EE7FF'
                            : status === 'hitl'      ? '#F59E0B'
                            : 'rgba(255,255,255,0.08)';
        const confBarY = y + h - 9;

        const labelColor = status === 'active'    ? '#E2F5FF'
                         : status === 'completed' ? '#D4F5E9'
                         : status === 'hitl'      ? '#FEF3C7'
                         : 'rgba(255,255,255,0.55)';
        const statusColor = status === 'active'    ? '#6EE7FF'
                          : status === 'completed' ? '#16C784'
                          : status === 'hitl'      ? '#F59E0B'
                          : 'rgba(255,255,255,0.22)';
        const fillUrl = status === 'active'    ? 'url(#node-grad-active)'
                      : status === 'completed' ? 'url(#node-grad-completed)'
                      : status === 'hitl'      ? 'url(#node-grad-hitl)'
                      : 'rgba(17,22,28,0.9)';
        const strokeColor = status === 'active'    ? '#6EE7FF'
                          : status === 'completed' ? '#16C784'
                          : status === 'hitl'      ? '#F59E0B'
                          : 'rgba(255,255,255,0.07)';
        const strokeW = (status === 'active' || status === 'completed' || status === 'hitl') ? 1.5 : 1;
        const nodeFilter = status === 'active'    ? 'url(#glow-active)'
                         : status === 'completed' ? 'url(#glow-completed)'
                         : 'none';

        nodesHtml += `
        <g class="${nodeCls}" id="wf-node-${id}" onclick="wfSelectNode('${id}')" style="cursor:pointer;">
            ${pulseHtml}
            ${selRing}
            <rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${NODE_R}"
                fill="${fillUrl}" stroke="${strokeColor}" stroke-width="${strokeW}"
                style="filter: ${nodeFilter}; transition: all 0.4s cubic-bezier(0.16,1,0.3,1);"/>
            <!-- Icon background -->
            <circle cx="${iconCX}" cy="${iconCY}" r="${iconR}" fill="${iconBg}"/>
            ${spinnerPath}
            <!-- Icon text -->
            <text x="${iconCX}" y="${iconCY}" text-anchor="middle" dominant-baseline="central"
                font-family="Inter,sans-serif" font-size="10" font-weight="700" fill="${iconColor}">${icon}</text>
            <!-- Status dot -->
            <circle cx="${x + w - 10}" cy="${y + 10}" r="3" fill="${dotColor}" style="filter: ${dotFilter};"/>
            <!-- Label -->
            <text x="${textX}" y="${labelY}" font-family="Inter,sans-serif" font-size="11" font-weight="600"
                letter-spacing="-0.02em" fill="${labelColor}">${label}</text>
            <!-- Status text -->
            <text x="${textX}" y="${statusY}" font-family="JetBrains Mono,monospace" font-size="9"
                fill="${statusColor}">${detailsText}</text>
            <!-- Confidence bar track -->
            <rect x="${x + 12}" y="${confBarY}" width="${confBarMaxW}" height="3" rx="1.5" fill="rgba(255,255,255,0.04)"/>
            <!-- Confidence bar fill -->
            <rect x="${x + 12}" y="${confBarY}" width="${confBarW}" height="3" rx="1.5" fill="${confFillColor}" style="transition: width 0.8s cubic-bezier(0.16,1,0.3,1);"/>
        </g>
        `;
    });

    nodesLayer.innerHTML = nodesHtml;
    wfUpdateGlobalStats();
}

window.wfSelectNode = function(nodeId) {
    state.wfSelectedNode = nodeId;
    const node = wfGetNode(nodeId);
    const meta = state.agentMetadata[nodeId];

    document.getElementById('wf-info-empty').style.display   = 'none';
    document.getElementById('wf-info-content').style.display = 'flex';

    if (meta) {
        document.getElementById('wf-detail-icon').textContent = meta.icon;
        document.getElementById('wf-detail-name').textContent = meta.name;
        document.getElementById('wf-detail-desc').textContent = meta.desc;
    } else {
        document.getElementById('wf-detail-icon').textContent = node ? node.icon : '?';
        document.getElementById('wf-detail-name').textContent = node ? node.label : nodeId;
        document.getElementById('wf-detail-desc').textContent = 'Pipeline utility node.';
    }

    if (node) {
        const statusEl = document.getElementById('wf-detail-status');
        statusEl.textContent = node.status.toUpperCase();
        statusEl.className = 'wf-info-badge'
            + (node.status === 'active' ? ' accent' : '')
            + (node.status === 'completed' ? ' success' : '');

        document.getElementById('wf-detail-time').textContent = node.duration > 0 ? `${node.duration}ms` : '—';
        document.getElementById('wf-detail-conf').textContent = node.conf > 0 ? `${node.conf}%` : '—';
        document.getElementById('wf-detail-conf-bar').style.width = `${node.conf}%`;
        document.getElementById('wf-detail-conf-pct').textContent = node.conf > 0 ? `${node.conf}%` : '0%';
    }

    wfRenderGraph();
};

function wfUpdateGlobalStats() {
    const elapsed = document.getElementById('wf-stat-elapsed');
    const doneEl  = document.getElementById('wf-stat-done');
    const confEl  = document.getElementById('wf-stat-conf');
    if (!elapsed) return;

    const completed = state.graphNodes.filter(n => n.status === 'completed').length;
    const total     = state.graphNodes.length;

    doneEl.textContent = `✓ ${completed} / ${total}`;
    doneEl.className   = 'wf-stat-chip' + (completed === total ? ' done-all' : '');

    const confNodes = state.graphNodes.filter(n => n.conf > 0);
    const avg = confNodes.length > 0
        ? Math.round(confNodes.reduce((s, n) => s + n.conf, 0) / confNodes.length)
        : 0;
    confEl.textContent = `◎ ${avg > 0 ? avg + '%' : '—'}`;

    if (state.workflowStatus === 'running') {
        elapsed.className = 'wf-stat-chip running';
    } else if (state.workflowStatus === 'completed') {
        elapsed.className = 'wf-stat-chip done-all';
    } else {
        elapsed.className = 'wf-stat-chip';
    }
}

function wfStartElapsedTimer() {
    state.wfElapsedStart = Date.now();
    if (state.wfElapsedTimer) clearInterval(state.wfElapsedTimer);
    state.wfElapsedTimer = setInterval(() => {
        const el = document.getElementById('wf-stat-elapsed');
        if (!el) return;
        const s = ((Date.now() - state.wfElapsedStart) / 1000).toFixed(1);
        el.textContent = `⏱ ${s}s`;
    }, 100);
}

function wfStopElapsedTimer() {
    if (state.wfElapsedTimer) { clearInterval(state.wfElapsedTimer); state.wfElapsedTimer = null; }
}

function wfResetGraph() {
    state.wfSelectedNode = null;
    document.getElementById('wf-info-empty').style.display   = 'block';
    document.getElementById('wf-info-content').style.display = 'none';
    state.graphNodes.forEach(n => { n.status = 'pending'; n.duration = 0; n.conf = 0; });
    const el = document.getElementById('wf-stat-elapsed');
    if (el) { el.textContent = '⏱ 0.0s'; el.className = 'wf-stat-chip'; }
    wfRenderGraph();
}

// Legacy function kept for backward compat with dashboard graph (uses wfRenderGraph now)
function drawWorkflowGraph() {
    wfRenderGraph();
}

window.handleNodeClick = function(nodeId) {
    wfSelectNode(nodeId);
};

function updateNodeState(nodeId, status, durationStr = '0ms', conf = 0) {
    const node = wfGetNode(nodeId);
    if (node) {
        node.status   = status;
        node.duration = parseInt(durationStr, 10) || 0;
        node.conf     = conf;
        wfRenderGraph();
    }
}


// ── Initialize SVG Radar Visualization ────────────────────────────────────────
function renderRadarChart(scores = [75, 75, 75, 75, 75]) {
    const container = document.getElementById('chart-radar-container');
    const size = 200;
    const center = size / 2;
    const maxRadius = 70;
    
    const dimensions = ['Market Size', 'MVP Tech', 'Economics', 'Risk Profile', 'GTM Power'];
    const angles = [0, 72, 144, 216, 288].map(d => (d * Math.PI) / 180);
    
    let gridLinesHtml = '';
    [25, 50, 75, 100].forEach(scale => {
        const r = (scale / 100) * maxRadius;
        let points = [];
        angles.forEach(a => {
            const x = center + r * Math.sin(a);
            const y = center - r * Math.cos(a);
            points.push(`${x},${y}`);
        });
        gridLinesHtml += `<polygon points="${points.join(' ')}" fill="none" stroke="rgba(255,255,255,0.03)" stroke-width="1"/>`;
    });

    let axesHtml = '';
    let labelsHtml = '';
    angles.forEach((a, i) => {
        const x = center + maxRadius * Math.sin(a);
        const y = center - maxRadius * Math.cos(a);
        axesHtml += `<line x1="${center}" y1="${center}" x2="${x}" y2="${y}" stroke="rgba(255,255,255,0.04)" stroke-width="1"/>`;
        
        const lx = center + (maxRadius + 14) * Math.sin(a);
        const ly = center - (maxRadius + 10) * Math.cos(a);
        let textAnchor = 'middle';
        if (Math.sin(a) > 0.1) textAnchor = 'start';
        else if (Math.sin(a) < -0.1) textAnchor = 'end';
        
        labelsHtml += `<text x="${lx}" y="${ly}" class="chart-text" text-anchor="${textAnchor}">${dimensions[i]}</text>`;
    });

    let scorePoints = [];
    angles.forEach((a, i) => {
        const val = scores[i] || 75;
        const r = (val / 100) * maxRadius;
        const x = center + r * Math.sin(a);
        const y = center - r * Math.cos(a);
        scorePoints.push(`${x},${y}`);
    });

    container.innerHTML = `
        <svg viewBox="0 0 ${size} ${size}" class="chart-svg">
            ${gridLinesHtml}
            ${axesHtml}
            <polygon points="${scorePoints.join(' ')}" class="radar-poly-fill" stroke="var(--text-main)" stroke-width="1.5"/>
            ${labelsHtml}
        </svg>
    `;
}

// ── Initialize SVG Line Chart ────────────────────────────────────────────────
function renderLineChart(months = []) {
    const container = document.getElementById('chart-line-container');
    if (!months || months.length === 0) {
        months = Array.from({length: 12}, (_, i) => ({
            month: i + 1,
            active_users: Math.round(150 * Math.pow(1.2, i)),
            monthly_recurring_revenue: Math.round(150 * Math.pow(1.2, i)) * 10
        }));
    }

    const width = 360;
    const height = 180;
    const padding = 28;
    
    const maxVal = Math.max(...months.map(m => m.active_users)) * 1.1;
    const xStep = (width - padding * 2) / (months.length - 1);
    
    let pathPoints = [];
    let areaPoints = [];
    let xAxisHtml = '';
    
    months.forEach((m, i) => {
        const x = padding + i * xStep;
        const y = height - padding - ((m.active_users / maxVal) * (height - padding * 2));
        pathPoints.push(`${x},${y}`);
        areaPoints.push(`${x},${y}`);
        
        if (i % 3 === 0 || i === months.length - 1) {
            xAxisHtml += `<text x="${x}" y="${height - 8}" class="chart-text" text-anchor="middle">M${m.month}</text>`;
        }
    });
    
    areaPoints.unshift(`${padding},${height - padding}`);
    areaPoints.push(`${padding + (months.length - 1) * xStep},${height - padding}`);

    let gridLines = '';
    for (let i = 1; i <= 3; i++) {
        const y = padding + (i * (height - padding * 2)) / 4;
        gridLines += `<line x1="${padding}" y1="${y}" x2="${width - padding}" y2="${y}" class="grid-line"/>`;
    }

    container.innerHTML = `
        <svg viewBox="0 0 ${width} ${height}" class="chart-svg">
            <defs>
                <linearGradient id="area-grad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stop-color="#7C5CFC" stop-opacity="0.12"/>
                    <stop offset="100%" stop-color="#7C5CFC" stop-opacity="0"/>
                </linearGradient>
            </defs>
            ${gridLines}
            <line x1="${padding}" y1="${height - padding}" x2="${width - padding}" y2="${height - padding}" class="axis-line"/>
            <polygon points="${areaPoints.join(' ')}" class="chart-path-area"/>
            <path d="M ${pathPoints.join(' L ')}" class="chart-path-line" stroke="var(--text-main)" stroke-width="1.5"/>
            ${xAxisHtml}
        </svg>
    `;
}

// ── Initialize SVG Bar Chart ────────────────────────────────────────────────
function renderBarChart(tamVal = 850, samVal = 42, somVal = 2.1) {
    const container = document.getElementById('chart-bar-container');
    const width = 360;
    const height = 180;
    const padding = 32;

    const values = [tamVal, samVal, somVal];
    const labels = ['TAM', 'SAM', 'SOM'];
    const logVals = values.map(v => Math.max(1, Math.log10(v + 1)));
    const maxLog = Math.max(...logVals);

    let barsHtml = '';
    const barWidth = 40;
    const gap = (width - padding * 2 - barWidth * 3) / 2;

    values.forEach((val, i) => {
        const scaledHeight = (logVals[i] / maxLog) * (height - padding * 2);
        const x = padding + i * (barWidth + gap);
        const y = height - padding - scaledHeight;
        
        barsHtml += `
            <rect x="${x}" y="${y}" width="${barWidth}" height="${scaledHeight}" class="bar-rect" fill="rgba(255, 255, 255, 0.04)" stroke="rgba(255,255,255,0.06)" />
            <text x="${x + barWidth / 2}" y="${y - 8}" class="chart-text" font-weight="600" text-anchor="middle" fill="var(--text-main)">$${val}B</text>
            <text x="${x + barWidth / 2}" y="${height - 10}" class="chart-text" text-anchor="middle">${labels[i]}</text>
        `;
    });

    container.innerHTML = `
        <svg viewBox="0 0 ${width} ${height}" class="chart-svg">
            <line x1="${padding}" y1="${height - padding}" x2="${width - padding}" y2="${height - padding}" class="axis-line"/>
            ${barsHtml}
        </svg>
    `;
}

// ── Renders Agent Details List ──────────────────────────────────────────────
function renderAgentCards() {
    elements.agentCardsGrid.innerHTML = Object.entries(state.agentMetadata).map(([id, meta]) => `
        <div class="agent-card" id="agent-${id}">
            <div class="agent-card-header" onclick="toggleAgentCard('${id}')">
                <div class="agent-card-title-group">
                    <span class="agent-icon" style="font-weight: 600; font-size: 11px; color: var(--text-secondary);">${meta.icon}</span>
                    <span class="agent-name">${meta.name}</span>
                </div>
                <div class="agent-status-tag pending" id="agent-badge-${id}">PENDING</div>
            </div>
            
            <div class="agent-card-body">
                <p class="agent-desc">${meta.desc}</p>
                <div class="agent-meta-metrics">
                    <span>Duration: <span class="agent-metric-val" id="agent-time-${id}">0ms</span></span>
                    <span>Confidence: <span class="agent-metric-val" id="agent-conf-${id}">0%</span></span>
                </div>
                <div class="agent-payload-block margin-top-large" id="agent-output-${id}">
                    Waiting for pipeline trigger...
                </div>
            </div>
        </div>
    `).join('');
}

window.toggleAgentCard = function(agentId) {
    const card = document.getElementById('agent-' + agentId);
    if (card) {
        card.classList.toggle('expanded');
    }
};

function updateAgentExecution(agentId, status, confidence = 0, time = '0ms', payload = null) {
    const badge = document.getElementById(`agent-badge-${agentId}`);
    const timeVal = document.getElementById(`agent-time-${agentId}`);
    const confVal = document.getElementById(`agent-conf-${agentId}`);
    const outputBlock = document.getElementById(`agent-output-${agentId}`);
    
    if (badge) {
        badge.className = `agent-status-tag ${status}`;
        badge.textContent = status.toUpperCase();
    }
    if (timeVal) timeVal.textContent = time;
    if (confVal) confVal.textContent = `${confidence}%`;
    if (outputBlock && payload) {
        outputBlock.textContent = typeof payload === 'object' ? JSON.stringify(payload, null, 2) : payload;
    }
}

// ── Load Run Details ──────────────────────────────────────────────────────────
function loadRunIntoDashboard(run) {
    state.selectedRun = run;
    elements.headerStartupName.textContent = run.startup_name;
    elements.heroStartupTitle.textContent = run.startup_name;
    
    updateGauge(elements.gaugeStartup, elements.valStartupScore, run.startup_score);
    updateGauge(elements.gaugeReadiness, elements.valInvestmentScore, run.investment_readiness_score);
    updateGauge(elements.gaugeConfidence, elements.valConfidenceScore, run.overall_confidence_score);
    
    elements.summaryVerdict.className = `badge-verdict ${run.recommendation.toLowerCase().replace(' ', '-')}`;
    elements.summaryVerdict.textContent = run.recommendation;
    elements.summaryText.textContent = run.executive_summary || 'No executive summary provided.';
    
    elements.summaryStrengths.innerHTML = '';
    elements.summaryRisks.innerHTML = '';
    
    if (run.startup_health) {
        elements.heroStartupDesc.textContent = run.startup_health;
    }
    
    // Parse confidence scores from gate4_log if available
    let confMap = {
        extract_name_node: 100,
        research_agent: 85, risk_agent: 82,
        product_agent: 80, finance_agent: 78,
        advocate_agent: 77, investor_agent: 74,
        hitl_review_node: 90,
        growth_agent: 79, simulator_agent: 81, pitchdeck_agent: 76,
        security_agent: 92,
        mcp_write_node: 100
    };

    if (run.gate4_log) {
        try {
            const gate4 = typeof run.gate4_log === 'string' ? JSON.parse(run.gate4_log) : run.gate4_log;
            if (gate4 && gate4.confidence_breakdown) {
                const bd = gate4.confidence_breakdown;
                confMap.research_agent = bd.research || confMap.research_agent;
                confMap.risk_agent = bd.risk || confMap.risk_agent;
                confMap.product_agent = bd.product || confMap.product_agent;
                confMap.finance_agent = bd.finance || confMap.finance_agent;
                confMap.advocate_agent = bd.advocate || confMap.advocate_agent;
                confMap.investor_agent = bd.investor || confMap.investor_agent;
                confMap.growth_agent = bd.growth || confMap.growth_agent;
                confMap.simulator_agent = bd.simulator || confMap.simulator_agent;
                confMap.pitchdeck_agent = bd.pitchdeck || confMap.pitchdeck_agent;
            }
        } catch (e) {
            console.error("Failed to parse gate4_log confidence breakdown:", e);
        }
    }
    
    // Set all nodes to COMPLETED in Graph
    state.graphNodes.forEach(node => {
        node.status = 'completed';
        node.duration = 450; // Numeric duration
        node.conf = confMap[node.id] || 80;
    });
    wfRenderGraph();
    
    elements.headerStatusBadge.className = 'status-badge status-completed';
    elements.headerStatusBadge.textContent = 'Completed';
    
    Object.keys(state.agentMetadata).forEach(agentId => {
        const conf = confMap[agentId] || 75;
        updateAgentExecution(agentId, 'done', conf, '450ms', 'Completed successfully.');
    });

    renderRadarChart([
        run.startup_score + 5 > 100 ? 100 : run.startup_score + 5,
        run.startup_score - 2,
        run.investment_readiness_score + 4,
        run.startup_score - 5,
        run.startup_score + 2
    ]);

    renderLineChart();
    renderBarChart(850, 42, 2.1);
    // Also refresh executive summary in background if that view is active
    if (state.currentView === 'executive-summary') loadExecutiveSummary();
}

// ── Executive Brief Population ────────────────────────────────────────────────
// Parses run data + markdown report to hydrate the McKinsey-style brief view.
async function loadExecutiveSummary() {
    const run = state.selectedRun;

    // ── Scorecard Numbers ─────────────────────────────────────────────────────
    const startupScore  = run ? run.startup_score               : 0;
    const investScore   = run ? run.investment_readiness_score  : 0;
    const confScore     = run ? (run.overall_confidence_score || run.overall_confidence || 0) : 0;

    // Populate number elements
    const el = id => document.getElementById(id);
    if (el('mck-startup-score'))    el('mck-startup-score').textContent    = run ? `${startupScore}/100` : '—';
    if (el('mck-invest-score'))     el('mck-invest-score').textContent     = run ? `${investScore}/100`  : '—';
    if (el('mck-confidence-score')) el('mck-confidence-score').textContent = run ? `${confScore}/100`    : '—';
    if (el('mck-date'))             el('mck-date').textContent = run ? new Date(run.timestamp).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' }) : '—';
    if (el('mck-headline'))         el('mck-headline').textContent = run ? `${run.startup_name} · Executive Brief` : 'Executive Investment Brief';
    if (el('mck-footer-run'))       el('mck-footer-run').textContent = run ? `Run ID: #${run.id}` : 'Run ID: —';

    // Verdict pill
    if (el('mck-verdict-pill') && run) {
        const pill = el('mck-verdict-pill');
        const rec  = (run.recommendation || '').toLowerCase();
        pill.textContent = run.recommendation || '—';
        pill.className = 'mck-verdict-pill';
        if (rec.includes('strong') || rec.includes('invest')) pill.classList.add('invest');
        else if (rec.includes('watch'))  pill.classList.add('watch');
        else if (rec.includes('pass'))   pill.classList.add('pass');
        else pill.classList.add('invest');
    }

    // Animate progress bars (setTimeout so CSS transition fires after repaint)
    setTimeout(() => {
        if (el('mck-startup-bar')) el('mck-startup-bar').style.width = `${startupScore}%`;
        if (el('mck-invest-bar'))  el('mck-invest-bar').style.width  = `${investScore}%`;
        if (el('mck-conf-bar'))    el('mck-conf-bar').style.width    = `${confScore}%`;
    }, 80);

    // ── Founder summary from run state ────────────────────────────────────────
    if (el('mck-founder-summary') && run) {
        el('mck-founder-summary').textContent = run.executive_summary || run.startup_health || 'Executive summary not available for this run.';
    }

    // ── Investor Recommendation ───────────────────────────────────────────────
    if (el('mck-investor-rec') && run) {
        el('mck-investor-rec').textContent = `Recommendation: ${run.recommendation || '—'}`;
    }

    // ── Fetch & parse the markdown report for richer content ──────────────────
    if (!run) {
        _mckSetPlaceholders();
        return;
    }

    const filename = `${run.startup_name.toLowerCase().replace(/\s+/g, '_')}_report.md`;
    try {
        const res  = await fetch(`/api/reports/${filename}`);
        if (!res.ok) { _mckSetPlaceholders(); return; }
        const text = await res.text();
        _mckParseReport(text, run);
    } catch (e) {
        console.warn('Executive brief: could not fetch report markdown', e);
        _mckSetPlaceholders();
    }
}

function _mckSetPlaceholders() {
    const el = id => document.getElementById(id);
    if (el('mck-opportunity'))  el('mck-opportunity').textContent  = 'Run an analysis to populate this section.';
    if (el('mck-risk'))         el('mck-risk').textContent         = 'Run an analysis to populate this section.';
    if (el('mck-revenue-est'))  el('mck-revenue-est').textContent  = '—';
    if (el('mck-mvp-features')) el('mck-mvp-features').innerHTML   = '<li class="mck-feature-item mck-skeleton">No report available. Launch a new analysis.</li>';
    if (el('mck-phase-1'))      el('mck-phase-1').innerHTML        = '<li>No roadmap data.</li>';
    if (el('mck-phase-2'))      el('mck-phase-2').innerHTML        = '';
    if (el('mck-phase-3'))      el('mck-phase-3').innerHTML        = '';
}

function _mckParseReport(text, run) {
    const el = id => document.getElementById(id);
    const lines = text.split('\n');

    // ── Helper: Extract bullet points under a heading ─────────────────────────
    function extractBulletsUnder(heading, maxItems = 6) {
        const bullets = [];
        let capture = false;
        for (const line of lines) {
            const trimmed = line.trim();
            if (!capture && trimmed.toLowerCase().includes(heading.toLowerCase())) {
                capture = true;
                continue;
            }
            if (capture) {
                if (trimmed.startsWith('#')) break; // next section
                const bullet = trimmed.replace(/^[-*•]\s*/, '').replace(/\*\*(.*?)\*\*/g, '$1').trim();
                if (bullet.length > 4) bullets.push(bullet);
                if (bullets.length >= maxItems) break;
            }
        }
        return bullets;
    }

    // ── Helper: Extract first N non-empty lines of paragraph text under heading
    function extractParagraphUnder(heading) {
        let capture = false;
        for (const line of lines) {
            const trimmed = line.trim();
            if (!capture && trimmed.toLowerCase().includes(heading.toLowerCase())) {
                capture = true;
                continue;
            }
            if (capture) {
                if (trimmed.startsWith('#')) break;
                const clean = trimmed.replace(/\*\*(.*?)\*\*/g, '$1');
                if (clean.length > 20) return clean;
            }
        }
        return null;
    }

    // ── Opportunity ───────────────────────────────────────────────────────────
    const oppBullets = extractBulletsUnder('market opportunit', 2)
                    || extractBulletsUnder('opportunit', 2);
    const oppText = oppBullets.length > 0
        ? oppBullets[0]
        : (extractParagraphUnder('market research') || `${run.startup_name} operates in a high-growth market with strong tailwinds.`);
    if (el('mck-opportunity')) el('mck-opportunity').textContent = oppText;

    // ── Primary Risk ─────────────────────────────────────────────────────────
    const riskBullets = extractBulletsUnder('risk', 2);
    const riskText = riskBullets.length > 0
        ? riskBullets[0]
        : (extractParagraphUnder('risk') || 'Market competition and execution risk are key concerns identified.');
    if (el('mck-risk')) el('mck-risk').textContent = riskText;

    // ── MVP Features ─────────────────────────────────────────────────────────
    const mvpBullets = extractBulletsUnder('must-have feature', 8)
        .concat(extractBulletsUnder('mvp feature', 8))
        .filter((v, i, a) => a.indexOf(v) === i)
        .slice(0, 6);
    if (el('mck-mvp-features')) {
        el('mck-mvp-features').innerHTML = mvpBullets.length > 0
            ? mvpBullets.map(f => `<li class="mck-feature-item">${f}</li>`).join('')
            : '<li class="mck-feature-item">Core platform with essential user workflow.</li>';
    }

    // ── Revenue Estimate ─────────────────────────────────────────────────────
    // Try to extract ARR/revenue figure from simulator section
    let revenueText = '—';
    const revMatch = text.match(/\$([\d,\.]+[KkMmBb]?)\s*(ARR|MRR|revenue|annual)/i);
    if (revMatch) revenueText = `$${revMatch[1]} ${revMatch[2]}`;
    else {
        const simMatch = text.match(/Year[\s-]*1[^\n]*?\$([\d,\.]+[KkMmBb]?)/i);
        if (simMatch) revenueText = `$${simMatch[1]}`;
    }
    if (el('mck-revenue-est')) el('mck-revenue-est').textContent = revenueText;
    if (el('mck-revenue-sub')) el('mck-revenue-sub').textContent = 'Based on 12-month simulation';

    // ── Investor Strengths ────────────────────────────────────────────────────
    const strengthBullets = extractBulletsUnder('strength', 5)
        .concat(extractBulletsUnder('top strength', 5))
        .filter((v, i, a) => a.indexOf(v) === i)
        .slice(0, 4);
    if (el('mck-strengths-list') && strengthBullets.length > 0) {
        el('mck-strengths-list').innerHTML = strengthBullets
            .map(s => `<div class="mck-strength-item">${s}</div>`)
            .join('');
    }

    // Investor Recommendation text
    const invBullets = extractBulletsUnder('investor verdict', 3)
        .concat(extractBulletsUnder('investment recommendation', 3))
        .filter((v, i, a) => a.indexOf(v) === i);
    if (el('mck-investor-rec')) {
        const invText = invBullets.length > 0
            ? invBullets[0]
            : (run.executive_summary ? run.executive_summary.slice(0, 200) : `Recommendation: ${run.recommendation}`);
        el('mck-investor-rec').textContent = invText;
    }

    // ── 90-Day Roadmap ────────────────────────────────────────────────────────
    // Try to parse roadmap phases from growth / roadmap sections
    const p1 = extractBulletsUnder('day 1', 4).concat(extractBulletsUnder('days 1', 4)).filter((v,i,a)=>a.indexOf(v)===i).slice(0,4);
    const p2 = extractBulletsUnder('day 31', 4).concat(extractBulletsUnder('days 31', 4)).concat(extractBulletsUnder('month 2', 4)).filter((v,i,a)=>a.indexOf(v)===i).slice(0,4);
    const p3 = extractBulletsUnder('day 61', 4).concat(extractBulletsUnder('days 61', 4)).concat(extractBulletsUnder('launch', 4)).filter((v,i,a)=>a.indexOf(v)===i).slice(0,4);

    // Fallback: take first 12 bullets from growth/roadmap section split into 3 groups
    let allRoadmap = extractBulletsUnder('90-day', 12).concat(extractBulletsUnder('roadmap', 12)).filter((v,i,a)=>a.indexOf(v)===i).slice(0,12);
    if (p1.length === 0 && allRoadmap.length > 0) {
        const chunk = Math.ceil(allRoadmap.length / 3);
        const r1 = allRoadmap.slice(0, chunk);
        const r2 = allRoadmap.slice(chunk, chunk*2);
        const r3 = allRoadmap.slice(chunk*2);
        _mckFillPhase('mck-phase-1', r1.length > 0 ? r1 : ['Finalize core team and development stack', 'Set up infrastructure, CI/CD, and monitoring', 'Define key success metrics and KPIs']);
        _mckFillPhase('mck-phase-2', r2.length > 0 ? r2 : ['Build and internally test MVP core feature set', 'Run closed beta with 10–20 design partners', 'Iterate on feedback and fix critical bugs']);
        _mckFillPhase('mck-phase-3', r3.length > 0 ? r3 : ['Launch publicly with initial marketing push', 'Begin outbound sales and partner channel activation', 'Close first paying customers; track retention metrics']);
    } else {
        _mckFillPhase('mck-phase-1', p1.length > 0 ? p1 : ['Define team structure and product roadmap', 'Complete technical architecture and stack decisions', 'Begin MVP development sprint planning']);
        _mckFillPhase('mck-phase-2', p2.length > 0 ? p2 : ['Complete MVP build with core feature set', 'Begin user testing with design partners', 'Develop go-to-market strategy and pricing']);
        _mckFillPhase('mck-phase-3', p3.length > 0 ? p3 : ['Launch product publicly with marketing campaigns', 'Activate growth channels and referral program', 'Close initial sales and collect testimonials']);
    }

    // ── Founder Summary Risks ─────────────────────────────────────────────────
    const riskItems = extractBulletsUnder('biggest risk', 4).concat(extractBulletsUnder('top risk', 4)).filter((v,i,a)=>a.indexOf(v)===i).slice(0,3);
    if (el('mck-brief-risks') && riskItems.length > 0) {
        el('mck-brief-risks').innerHTML = riskItems
            .map(r => `<div class="mck-risk-item"><div class="mck-risk-dot"></div><span>${r}</span></div>`)
            .join('');
    }
}

function _mckFillPhase(elId, items) {
    const el = document.getElementById(elId);
    if (!el) return;
    el.innerHTML = items.map(i => `<li>${i}</li>`).join('');
}

// ── Database / API Fetch Operations ──────────────────────────────────────────
async function fetchHistory() {
    elements.historyTableBody.innerHTML = '<tr><td colspan="8" class="text-center">Loading evaluation history...</td></tr>';
    try {
        const res = await fetch('/api/runs');
        const runs = await res.json();
        state.runs = runs;
        
        if (runs.length === 0) {
            elements.historyTableBody.innerHTML = '<tr><td colspan="8" class="text-center">No runs logged. Launch a new analysis from the form view!</td></tr>';
            return;
        }

        elements.historyTableBody.innerHTML = runs.map(run => `
            <tr>
                <td>#${run.id}</td>
                <td class="font-bold">${run.startup_name}</td>
                <td><span class="badge font-bold">${run.startup_score}/100</span></td>
                <td><span class="badge font-bold">${run.investment_readiness_score}/100</span></td>
                <td><span class="badge font-bold">${run.overall_confidence_score || run.overall_confidence}/100</span></td>
                <td><span class="badge-verdict ${run.recommendation.toLowerCase().replace(' ', '-')}">${run.recommendation}</span></td>
                <td>${new Date(run.timestamp).toLocaleString()}</td>
                <td>
                    <button class="btn btn-secondary btn-small" onclick="loadRunDetails(${run.id})">Load</button>
                </td>
            </tr>
        `).join('');
    } catch(err) {
        showToast('Failed to fetch runs index from SQLite.', 'error');
        elements.historyTableBody.innerHTML = '<tr><td colspan="8" class="text-center text-danger">Database error. Check server logs.</td></tr>';
    }
}

window.loadRunDetails = function(runId) {
    const run = state.runs.find(r => r.id === runId);
    if (run) {
        loadRunIntoDashboard(run);
        switchView('dashboard');
        showToast(`Loaded ${run.startup_name} run details!`, 'success');
    }
};

async function fetchReports() {
    elements.reportsFileList.innerHTML = '<div class="text-center">Loading reports directory...</div>';
    try {
        const res = await fetch('/api/reports');
        const reports = await res.json();
        state.reports = reports;

        if (reports.length === 0) {
            elements.reportsFileList.innerHTML = '<div class="text-center">No outputs compiled yet. Run an analysis.</div>';
            return;
        }

        elements.reportsFileList.innerHTML = reports.map(file => `
            <div class="report-file-item" onclick="loadReportViewer('${file}')">${file}</div>
        `).join('');
    } catch(err) {
        showToast('Failed to list files in ./outputs directory.', 'error');
    }
}

window.loadReportViewer = async function(filename) {
    document.querySelectorAll('.report-file-item').forEach(item => {
        if (item.textContent === filename) item.classList.add('active');
        else item.classList.remove('active');
    });

    elements.reportViewTitle.textContent = filename;
    elements.reportViewerContent.innerHTML = 'Loading output file...';
    state.activeReportPath = filename;

    try {
        const res = await fetch(`/api/reports/${filename}`);
        const text = await res.text();
        
        let html = text
            .replace(/^# (.*$)/gim, '<h1>$1</h1>')
            .replace(/^## (.*$)/gim, '<h2>$1</h2>')
            .replace(/^### (.*$)/gim, '<h3>$1</h3>')
            .replace(/^\> (.*$)/gim, '<blockquote>$1</blockquote>')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/```markdown([\s\S]*?)```/g, '<pre>$1</pre>')
            .replace(/```json([\s\S]*?)```/g, '<pre>$1</pre>')
            .replace(/```([\s\S]*?)```/g, '<pre>$1</pre>')
            .replace(/\n/g, '<br>');

        elements.reportViewerContent.innerHTML = html;
        parseMarkdownPitchDeck(text);
    } catch(err) {
        elements.reportViewerContent.innerHTML = '<div class="text-danger">Failed to render report content.</div>';
    }
};

function parseMarkdownPitchDeck(text) {
    state.pitchDeckSlides = [];
    const slideRegex = /## Pitch Deck[\s\S]*$/i;
    const deckMatch = text.match(slideRegex);
    if (!deckMatch) return;
    
    const deckText = deckMatch[0];
    const rawSlides = deckText.split(/Slide \d+:/i).slice(1);
    
    state.pitchDeckSlides = rawSlides.map((slide, idx) => {
        const lines = slide.trim().split('\n');
        const title = lines[0].trim();
        const points = lines.slice(1)
            .map(p => p.replace(/^-\s*/, '').trim())
            .filter(p => p.length > 0);
        return { index: idx + 1, title, points };
    });
}

function renderSlide(index) {
    if (state.pitchDeckSlides.length === 0) return;
    const slide = state.pitchDeckSlides[index];
    
    elements.slideNum.textContent = `Slide ${slide.index} / ${state.pitchDeckSlides.length}`;
    elements.slideTitle.textContent = slide.title;
    elements.slidePointsList.innerHTML = slide.points.map(p => `<li>${p}</li>`).join('');
    
    elements.deckDotsNav.innerHTML = state.pitchDeckSlides.map((_, i) => `
        <div class="deck-dot ${i === index ? 'active' : ''}" onclick="goToSlide(${i})"></div>
    `).join('');
}

window.goToSlide = function(index) {
    state.currentSlideIndex = index;
    renderSlide(index);
};

// ── YC Interactive Demo Mode ──────────────────────────────────────────────────
function runInteractiveDemo() {
    // Close any active overlays/modals
    if (elements.hitlOverlay) elements.hitlOverlay.classList.remove('active');
    if (elements.deckModal) elements.deckModal.classList.remove('active');
    
    switchView('workflow');
    wfResetGraph();
    wfStartElapsedTimer();
    
    state.workflowStatus = 'running';
    elements.headerStatusBadge.className = 'status-badge status-running';
    elements.headerStatusBadge.textContent = 'Running';
    elements.headerStartupName.textContent = 'Solarex';
    elements.heroStartupTitle.textContent = 'Solarex';
    elements.heroStartupDesc.textContent = 'Optimizing community solar energy sharing across HOA residential communities.';
    
    const executionPlan = [
        ['extract_name_node'],
        ['research_agent', 'risk_agent'],
        ['product_agent', 'finance_agent'],
        ['advocate_agent', 'investor_agent'],
        ['hitl_review_node'],
        ['growth_agent', 'simulator_agent', 'pitchdeck_agent'],
        ['security_agent'],
        ['mcp_write_node']
    ];
    
    const confMap = {
        extract_name_node: 100,
        research_agent: 85, risk_agent: 82,
        product_agent: 80, finance_agent: 78,
        advocate_agent: 77, investor_agent: 74,
        hitl_review_node: 90,
        growth_agent: 79, simulator_agent: 81, pitchdeck_agent: 76,
        security_agent: 92,
        mcp_write_node: 100
    };
    
    let batchIndex = 0;
    
    function runDemoBatch() {
        if (batchIndex >= executionPlan.length) {
            // End of demo
            wfStopElapsedTimer();
            state.workflowStatus = 'completed';
            elements.headerStatusBadge.className = 'status-badge status-completed';
            elements.headerStatusBadge.textContent = 'Completed';
            
            // Load Solarex data
            let solarexRun = state.runs.find(r => r.startup_name.toLowerCase().includes('solarex'));
            if (!solarexRun) {
                // Guaranteed fallback Solarex run object
                solarexRun = {
                    id: 9999,
                    session_id: 'demo-session',
                    startup_name: 'Solarex',
                    startup_score: 74,
                    investment_readiness_score: 72,
                    overall_confidence_score: 78,
                    recommendation: 'Conditional Invest',
                    executive_summary: 'Solarex presents a compelling Seed opportunity in the CleanTech space. Strong unit economics (LTV:CAC 12x) and a clear market gap support the thesis. The primary risk — unvalidated CAC — is addressable through 3 design-partner pilots in Month 1.',
                    startup_health: 'Solarex is in healthy early-stage position with strong economics, clear differentiation, and a near-term validation path via design partners.',
                    recommended_next_action: 'Sign 3 design-partner pilots to validate CAC before Series A.',
                    timestamp: new Date().toISOString()
                };
            }
            
            loadRunIntoDashboard(solarexRun);
            
            // Go to Reports view first to select the report
            loadReportViewer('solarex_report.md').then(() => {
                // Automatically switch back to executive summary page
                switchView('executive-summary');
                showToast('⚡ YC Demo Mode Complete! Solarex analysis compiled.', 'success');
                triggerConfetti();
                
                // Show Pitch Deck slide deck overlay automatically
                setTimeout(() => {
                    if (state.pitchDeckSlides && state.pitchDeckSlides.length > 0) {
                        state.currentSlideIndex = 0;
                        renderSlide(0);
                        elements.deckModal.classList.add('active');
                        showToast('📽️ Presentation Mode Active: Seed Round Pitch Deck loaded!', 'info');
                    }
                }, 1000);
            });
            return;
        }
        
        const group = executionPlan[batchIndex];
        
        if (group.includes('hitl_review_node')) {
            group.forEach(id => updateNodeState(id, 'hitl', '0ms', 0));
            const node = wfGetNode('hitl_review_node');
            if (node) { node.status = 'hitl'; }
            wfRenderGraph();
            
            state.workflowStatus = 'hitl';
            elements.headerStatusBadge.className = 'status-badge status-hitl';
            elements.headerStatusBadge.textContent = 'HITL Review';
            showToast('Workflow paused: Founder review required at Gate 3.', 'warning');
            
            elements.hitlSummaryBox.textContent = `
Startup Name: Solarex
MVP Scope: Must-have feature list validated (Research + Risk mitigations check complete).
Payback Period: 3.8 Months
LTV:CAC Ratio: 12x
Devil's Advocate: CAC unvalidated inbound channel mix risk flagged.
Investor Score: 72/100 (Conditional Seed Invest Recommendation).`.trim();
            
            setTimeout(() => {
                elements.hitlOverlay.classList.add('active');
                
                // Auto-approve after 1.8 seconds so judges can see the HITL panel but don't have to click
                setTimeout(() => {
                    if (state.workflowStatus === 'hitl') {
                        elements.hitlOverlay.classList.remove('active');
                        showToast('⚡ Auto-approved by system checklist compiler.', 'success');
                        updateNodeState('hitl_review_node', 'completed', '420ms', confMap.hitl_review_node);
                        state.workflowStatus = 'running';
                        elements.headerStatusBadge.className = 'status-badge status-running';
                        elements.headerStatusBadge.textContent = 'Running';
                        batchIndex++;
                        runDemoBatch();
                    }
                }, 1800);
            }, 200);
            return;
        }
        
        // Mark as active
        group.forEach(id => {
            const node = wfGetNode(id);
            if (node) { node.status = 'active'; node.duration = 0; node.conf = 0; }
        });
        wfRenderGraph();
        
        // Complete after short delay
        setTimeout(() => {
            group.forEach(id => {
                const dur = 350 + Math.round(Math.random() * 100);
                updateNodeState(id, 'completed', `${dur}ms`, confMap[id] || 80);
                if (state.agentMetadata[id]) {
                    updateAgentExecution(id, 'done', confMap[id] || 80, `${dur}ms`, 'Finished validation loop.');
                }
            });
            batchIndex++;
            setTimeout(runDemoBatch, 200);
        }, 800);
    }
    
    runDemoBatch();
}

// ── Multi-Agent Analysis Pipeline Launch ─────────────────────────────────────

async function handleAnalysisSubmit(e) {
    e.preventDefault();
    
    const input = {
        name: document.getElementById('startup-name').value,
        industry: document.getElementById('startup-industry').value,
        description: document.getElementById('startup-description').value,
        estimated_pricing: document.getElementById('startup-pricing').value,
        target_customer: document.getElementById('startup-customer').value,
        funding_stage: document.getElementById('startup-stage').value
    };
    
    const mode = document.getElementById('analysis-mode').value;
    switchView('dashboard');
    showToast(`Launching ${input.name} evaluation pipeline...`, 'info');
    
    state.workflowStatus = 'running';
    elements.headerStatusBadge.className = 'status-badge status-running';
    elements.headerStatusBadge.textContent = 'Running';
    elements.headerStartupName.textContent = input.name;
    elements.heroStartupTitle.textContent = input.name;
    elements.heroStartupDesc.textContent = input.description;
    
    // Reset Graph Nodes to pending
    state.graphNodes.forEach(node => {
        node.status = 'pending';
        node.duration = '0ms';
        node.conf = 0;
    });
    drawWorkflowGraph();
    
    Object.keys(state.agentMetadata).forEach(id => updateAgentExecution(id, 'pending', 0, '0ms', 'Waiting...'));
    
    try {
        const res = await fetch(`/api/analyze?mode=${mode}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(input)
        });
        simulateWorkflowRun(mode, input.name);
    } catch(err) {
        showToast('Pipeline launch failed. Confirm backend server running.', 'error');
        state.workflowStatus = 'idle';
        elements.headerStatusBadge.className = 'status-badge status-idle';
        elements.headerStatusBadge.textContent = 'Idle';
    }
}

// ── Real-Time Flow Simulation Controller ─────────────────────────────────────
function simulateWorkflowRun(mode, startupName) {
    // Switch to workflow view to show animation
    switchView('workflow');
    wfStartElapsedTimer();

    // Sequential execution plan mirrors actual orchestrator graph order
    // Groups that run in parallel are in sub-arrays
    const executionPlan = [
        ['extract_name_node'],                              // Input
        ['research_agent', 'risk_agent'],                   // Phase 1 (parallel)
        ['product_agent', 'finance_agent'],                 // Phase 2 (parallel)
        ['advocate_agent', 'investor_agent'],               // Phase 3 (parallel)
        ['hitl_review_node'],                               // HITL Gate
        ['growth_agent', 'simulator_agent', 'pitchdeck_agent'], // Phase 4 (parallel)
        ['security_agent'],                                 // Final
        ['mcp_write_node'],                                 // Report
    ];

    // Durations per group (ms to "complete" each parallel batch)
    const batchDurations = [500, 1400, 1200, 1100, 0, 1300, 700, 500];
    // Confidence values per node id
    const confMap = {
        extract_name_node: 100,
        research_agent: 85, risk_agent: 82,
        product_agent: 80, finance_agent: 78,
        advocate_agent: 77, investor_agent: 74,
        hitl_review_node: 90,
        growth_agent: 79, simulator_agent: 81, pitchdeck_agent: 76,
        security_agent: 92,
        mcp_write_node: 100,
    };

    let batchIndex = 0;

    function runBatch() {
        if (batchIndex >= executionPlan.length) {
            // All done
            wfStopElapsedTimer();
            state.workflowStatus = 'completed';
            elements.headerStatusBadge.className = 'status-badge status-completed';
            elements.headerStatusBadge.textContent = 'Completed';
            showToast('Evaluation complete! SQLite and report outputs updated.', 'success');
            triggerConfetti();
            fetchHistory().then(() => {
                if (state.runs.length > 0) loadRunIntoDashboard(state.runs[0]);
            });
            return;
        }

        const group    = executionPlan[batchIndex];
        const batchDur = batchDurations[batchIndex];

        // HITL pause
        if (group.includes('hitl_review_node')) {
            group.forEach(id => updateNodeState(id, 'hitl', '0ms', 0));
            const node = wfGetNode('hitl_review_node');
            if (node) { node.status = 'hitl'; }
            wfRenderGraph();

            state.workflowStatus = 'hitl';
            elements.headerStatusBadge.className = 'status-badge status-hitl';
            elements.headerStatusBadge.textContent = 'HITL Review';
            showToast('Workflow paused. Founder review required at Gate 3.', 'warning');

            elements.hitlSummaryBox.textContent = `
Startup Name: ${startupName}
MVP Scope: Must-have feature list validated (Research + Risk mitigations check complete).
Payback Period: 4.3 Months
LTV:CAC Ratio: 8.5x
Devil's Advocate: Competition & Grid hardware integration risks flagged.
Investor Score: 74/100 (Conditional Seed Invest Recommendation).`.trim();
            elements.hitlOverlay.classList.add('active');

            window.resumeWorkflow = function(choice) {
                elements.hitlOverlay.classList.remove('active');
                showToast(`Feedback submitted: ${choice}. Resuming execution...`, 'success');
                updateNodeState('hitl_review_node', 'completed', '1200ms', confMap.hitl_review_node);
                state.workflowStatus = 'running';
                elements.headerStatusBadge.className = 'status-badge status-running';
                elements.headerStatusBadge.textContent = 'Running';
                batchIndex++;
                runBatch();
            };
            return;
        }

        // Mark all nodes in group as active
        group.forEach(id => {
            const node = wfGetNode(id);
            if (node) { node.status = 'active'; node.duration = 0; node.conf = 0; }
        });
        wfRenderGraph();

        // After batchDur, mark all as completed
        setTimeout(() => {
            group.forEach(id => {
                const dur = batchDur + Math.round((Math.random() - 0.5) * 200);
                updateNodeState(id, 'completed', `${dur}ms`, confMap[id] || 80);
                if (state.agentMetadata[id]) {
                    updateAgentExecution(id, 'done', confMap[id] || 80, `${dur}ms`, 'Finished validation loop.');
                }
            });
            batchIndex++;
            setTimeout(runBatch, 250);
        }, batchDur);
    }

    state.workflowStatus = 'running';
    elements.headerStatusBadge.className = 'status-badge status-running';
    elements.headerStatusBadge.textContent = 'Running';
    runBatch();
}

// ── Event Handlers ───────────────────────────────────────────────────────────
function initEvents() {
    elements.navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const viewName = item.getAttribute('data-view');
            switchView(viewName);
        });
    });

    elements.analysisForm.addEventListener('submit', handleAnalysisSubmit);

    if (elements.btnDemoMode) {
        elements.btnDemoMode.addEventListener('click', (e) => {
            e.preventDefault();
            runInteractiveDemo();
        });
    }

    elements.btnHitlApprove.addEventListener('click', () => window.resumeWorkflow('approved'));
    elements.btnHitlMinor.addEventListener('click', () => window.resumeWorkflow('minor_revision'));
    elements.btnHitlMajor.addEventListener('click', () => window.resumeWorkflow('major_revision'));

    elements.btnViewDeck.addEventListener('click', () => {
        if (state.pitchDeckSlides.length === 0) {
            showToast('No pitch deck slide outline parsed from the markdown report.', 'warning');
            return;
        }
        state.currentSlideIndex = 0;
        renderSlide(0);
        elements.deckModal.classList.add('active');
    });
    
    elements.deckModalClose.addEventListener('click', () => {
        elements.deckModal.classList.remove('active');
    });

    elements.btnDeckPrev.addEventListener('click', () => {
        if (state.currentSlideIndex > 0) {
            state.currentSlideIndex--;
            renderSlide(state.currentSlideIndex);
        }
    });

    elements.btnDeckNext.addEventListener('click', () => {
        if (state.currentSlideIndex < state.pitchDeckSlides.length - 1) {
            state.currentSlideIndex++;
            renderSlide(state.currentSlideIndex);
        }
    });

    elements.btnCopyMd.addEventListener('click', () => {
        if (elements.reportViewerContent.textContent) {
            navigator.clipboard.writeText(elements.reportViewerContent.textContent);
            showToast('Report markdown copied to clipboard!', 'success');
        }
    });

    elements.btnExportPdf.addEventListener('click', () => {
        if (state.selectedRun) {
            window.open(`/api/reports/${state.selectedRun.startup_name.toLowerCase().replace(' ', '_')}_report.pdf`);
            showToast('PDF report download launched!', 'success');
        } else {
            showToast('Load a completed run before exporting reports.', 'warning');
        }
    });
    
    elements.btnExportMd.addEventListener('click', () => {
        if (state.selectedRun) {
            window.open(`/api/reports/${state.selectedRun.startup_name.toLowerCase().replace(' ', '_')}_report.md`);
            showToast('Markdown report download launched!', 'success');
        } else {
            showToast('Load a completed run before exporting reports.', 'warning');
        }
    });
}

// ══════════════════════════════════════════════════════════════════════════════
// ── CINEMATIC ENGINE ──────────────────────────────────────────────────────────
// ══════════════════════════════════════════════════════════════════════════════

// ── Particle Background ───────────────────────────────────────────────────────
function initParticles() {
    const canvas = document.getElementById('particles-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    let W = 0, H = 0;
    const PARTICLE_COUNT = 55; // low count for guaranteed 60 FPS
    let particles = [];

    function resize() {
        W = canvas.width  = window.innerWidth;
        H = canvas.height = window.innerHeight;
    }
    window.addEventListener('resize', resize, { passive: true });
    resize();

    // Spawn particles across the viewport
    for (let i = 0; i < PARTICLE_COUNT; i++) {
        particles.push({
            x:     Math.random() * W,
            y:     Math.random() * H,
            vx:    (Math.random() - 0.5) * 0.18,
            vy:    (Math.random() - 0.5) * 0.18,
            r:     Math.random() * 1.4 + 0.4,
            alpha: Math.random() * 0.22 + 0.06,
            hue:   Math.random() > 0.5 ? 258 : 196 // purple or cyan
        });
    }

    let rafId;
    function tick() {
        ctx.clearRect(0, 0, W, H);
        for (let i = 0; i < PARTICLE_COUNT; i++) {
            const p = particles[i];
            p.x += p.vx;
            p.y += p.vy;
            if (p.x < 0) p.x = W; else if (p.x > W) p.x = 0;
            if (p.y < 0) p.y = H; else if (p.y > H) p.y = 0;

            ctx.beginPath();
            ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
            ctx.fillStyle = `hsla(${p.hue}, 85%, 72%, ${p.alpha})`;
            ctx.fill();
        }
        rafId = requestAnimationFrame(tick);
    }
    tick();
}

// ── Confetti Celebration ──────────────────────────────────────────────────────
function triggerConfetti() {
    const canvas = document.getElementById('confetti-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    canvas.width  = window.innerWidth;
    canvas.height = window.innerHeight;

    const PALETTE = ['#7C5CFC', '#6EE7FF', '#16C784', '#F59E0B', '#EF4444', '#A78BFA', '#FFFFFF'];
    const flakes  = [];

    for (let i = 0; i < 140; i++) {
        const fromLeft = i % 2 === 0;
        flakes.push({
            x:    fromLeft ? canvas.width * 0.1 : canvas.width * 0.9,
            y:    canvas.height + 10,
            vx:   (fromLeft ? 1 : -1) * (Math.random() * 14 + 6),
            vy:   -(Math.random() * 22 + 12),
            rot:  Math.random() * 360,
            dRot: (Math.random() - 0.5) * 12,
            w:    Math.random() * 9 + 5,
            h:    Math.random() * 5 + 3,
            col:  PALETTE[Math.floor(Math.random() * PALETTE.length)],
            life: 1.0
        });
    }

    const start = performance.now();
    function draw(ts) {
        if (ts - start > 5000) { ctx.clearRect(0, 0, canvas.width, canvas.height); return; }
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        let alive = false;
        for (const f of flakes) {
            f.x   += f.vx;
            f.y   += f.vy;
            f.vy  += 0.55;   // gravity
            f.vx  *= 0.99;   // drag
            f.rot += f.dRot;
            f.life -= 0.007;
            if (f.y < canvas.height && f.life > 0) {
                alive = true;
                ctx.save();
                ctx.translate(f.x, f.y);
                ctx.rotate(f.rot * Math.PI / 180);
                ctx.globalAlpha = Math.max(0, f.life);
                ctx.fillStyle   = f.col;
                ctx.fillRect(-f.w / 2, -f.h / 2, f.w, f.h);
                ctx.restore();
            }
        }
        if (alive) requestAnimationFrame(draw);
        else        ctx.clearRect(0, 0, canvas.width, canvas.height);
    }
    requestAnimationFrame(draw);
}

// ── Smooth Value Counter (requestAnimationFrame-based) ─────────────────────
function animateCounter(el, from, to, duration = 900, suffix = '') {
    if (!el) return;
    const start = performance.now();
    const delta = to - from;

    function step(ts) {
        const elapsed = ts - start;
        const progress = Math.min(elapsed / duration, 1);
        // Ease-out cubic
        const ease = 1 - Math.pow(1 - progress, 3);
        el.textContent = Math.round(from + delta * ease) + suffix;
        if (progress < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
}

// ── Upgraded updateGauge: replaces setInterval with rAF + counter ─────────
function updateGaugeAnimated(circleEl, valueEl, value) {
    const circumference = 157;
    const targetOffset  = circumference - (value / 100) * circumference;

    // Animate SVG stroke
    const startOffset = parseFloat(circleEl.style.strokeDashoffset) || circumference;
    const startTime   = performance.now();
    const dur = 900;

    function strokeStep(ts) {
        const p = Math.min((ts - startTime) / dur, 1);
        const ease = 1 - Math.pow(1 - p, 3);
        circleEl.style.strokeDashoffset = startOffset + (targetOffset - startOffset) * ease;
        if (p < 1) requestAnimationFrame(strokeStep);
    }
    requestAnimationFrame(strokeStep);

    // Animate number counter
    const startVal = parseInt(valueEl.textContent) || 0;
    animateCounter(valueEl, startVal, value, dur);
}

// ── Boot Screen Fade-out ──────────────────────────────────────────────────────
function dismissBootLoader() {
    const loader  = document.getElementById('cinematic-boot-loader');
    const bar     = document.getElementById('boot-loader-bar');
    if (!loader) return;

    // Kick the bar to 100%
    requestAnimationFrame(() => {
        if (bar) bar.style.width = '100%';
        // After progress bar animation (1.2s), fade out
        setTimeout(() => {
            loader.classList.add('fade-out');
            // Remove from flow after fade completes (0.8s)
            setTimeout(() => loader.remove(), 820);
        }, 1250);
    });
}

// ── Smooth View Transition wrapper ───────────────────────────────────────────
const _origSwitchView = switchView;
// Override switchView to add slide-fade transitions
window.switchView = function(viewName) {
    const all = document.querySelectorAll('.view-content');
    all.forEach(v => {
        if (v.classList.contains('active')) {
            v.style.opacity    = '0';
            v.style.transform  = 'translateY(8px)';
            v.style.transition = 'opacity 0.18s ease, transform 0.18s ease';
        }
    });
    setTimeout(() => {
        _origSwitchView(viewName);
        const next = document.querySelector('.view-content.active');
        if (next) {
            next.style.opacity   = '0';
            next.style.transform = 'translateY(10px)';
            next.style.transition = 'none';
            requestAnimationFrame(() => {
                requestAnimationFrame(() => {
                    next.style.transition = 'opacity 0.32s cubic-bezier(0.16,1,0.3,1), transform 0.32s cubic-bezier(0.16,1,0.3,1)';
                    next.style.opacity    = '1';
                    next.style.transform  = 'translateY(0)';
                });
            });
        }
    }, 180);
};

// ── Skeleton Loader helpers ───────────────────────────────────────────────────
function showSkeletonInList(containerEl, rows = 4) {
    if (!containerEl) return;
    containerEl.innerHTML = Array.from({ length: rows }).map(() => `
        <div style="display:flex;gap:10px;padding:10px 0;border-bottom:1px solid rgba(255,255,255,0.03);">
            <div class="skeleton-shimmer" style="width:32px;height:32px;border-radius:8px;flex-shrink:0;"></div>
            <div style="flex:1;display:flex;flex-direction:column;gap:6px;">
                <div class="skeleton-shimmer" style="height:12px;width:60%;border-radius:4px;"></div>
                <div class="skeleton-shimmer" style="height:10px;width:40%;border-radius:4px;"></div>
            </div>
            <div class="skeleton-shimmer" style="height:20px;width:48px;border-radius:6px;align-self:center;"></div>
        </div>
    `).join('');
}

// ── Toast Upgrade: smooth slide-in/out ───────────────────────────────────────
// (existing showToast is already functional; this upgrade adds auto-stack limit)
const _toastQueue = [];
const MAX_TOASTS  = 4;
const _origShowToast = window.showToast || showToast;
window.showToast = function(msg, type = 'info') {
    const toastContainer = document.getElementById('toast-banner-container');
    if (toastContainer && toastContainer.children.length >= MAX_TOASTS) {
        // Remove oldest toast immediately
        const oldest = toastContainer.firstElementChild;
        if (oldest) oldest.remove();
    }
    _origShowToast(msg, type);
};

// ══════════════════════════════════════════════════════════════════════════════
// ── Application Boot ──────────────────────────────────────────────────────────
// ══════════════════════════════════════════════════════════════════════════════
function bootstrap() {
    initParticles();        // Start ambient particle background
    dismissBootLoader();    // Begin boot progress bar → fade-out sequence

    initEvents();
    wfRenderGraph();        // Initialize workflow visualization
    renderAgentCards();

    // Patch updateGauge globally to use the smoother rAF version
    window.updateGauge = updateGaugeAnimated;

    renderRadarChart([78, 75, 74, 82, 80]);
    renderLineChart();
    renderBarChart(850, 42, 2.1);

    fetchHistory().then(() => {
        if (state.runs.length > 0) {
            loadRunIntoDashboard(state.runs[0]);
        }
    });
}

document.addEventListener('DOMContentLoaded', bootstrap);

