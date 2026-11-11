const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const html = fs.readFileSync(path.join(__dirname, '..', 'templates', 'index.html'), 'utf8');
const block = html.match(/\/\/ Floating assistant controls([\s\S]*?)\/\/ End floating assistant controls/);
assert.ok(block, 'Floating panel controller is required');
const dragBlock = html.match(/\/\/ Draggable assistant launcher([\s\S]*?)\/\/ End draggable assistant launcher/);
assert.ok(dragBlock, 'Draggable assistant controller is required');
const windowBlock = html.match(/\/\/ Movable assistant window([\s\S]*?)\/\/ End movable assistant window/);

function setup(savedPosition = null) {
    let document;
    const pointerHandlers = {};
    const elementHandlers = {};
    const windowHandlers = {};
    const storage = new Map(savedPosition === null ? [] : [['beviq_assistant_position', savedPosition]]);
    const window = {innerWidth:1280, innerHeight:900, addEventListener(name, handler) { windowHandlers[name] = handler; }};
    const classes = new Map();
    const classSet = id => { if (!classes.has(id)) classes.set(id, new Set()); return classes.get(id); };
    const element = (id) => ({
        id, hidden: false, disabled: false, isConnected: true, value: 'draft stays here',
        attributes: {}, textContent: '', style: {},
        classList: {
            add(name) { classSet(id).add(name); },
            remove(name) { classSet(id).delete(name); },
            contains(name) { return classSet(id).has(name); },
            toggle(name, enabled) { if (enabled) classSet(id).add(name); else classSet(id).delete(name); },
        },
        addEventListener(name, handler) {
            (elementHandlers[id] ||= {})[name] = handler;
            if (id === 'dashboard-floating-assistant') pointerHandlers[name] = handler;
        },
        setPointerCapture(pointerId) { this.captured = pointerId; },
        hasPointerCapture(pointerId) { return this.captured === pointerId; },
        releasePointerCapture() { this.captured = null; },
        getBoundingClientRect() {
            const panel = this.id === 'tab-chat';
            const width = parseFloat(this.style.width) || (panel ? Math.min(560, window.innerWidth - 24) : 148);
            const height = parseFloat(this.style.height) || (panel ? Math.min(740, window.innerHeight - 112) : 44);
            const left = this.style.left ? parseFloat(this.style.left) : window.innerWidth - width - 20;
            const top = this.style.top ? parseFloat(this.style.top) : window.innerHeight - height - 20;
            return {left,top,width,height,right:left+width,bottom:top+height};
        },
        appendChild(child) { child.parentElement = this; },
        setAttribute(name, value) { this.attributes[name] = value; },
        focus() { document.activeElement = this; },
    });
    const ids = Object.fromEntries([
        'tab-chat', 'dashboard-floating-assistant', 'assistant-launcher-home', 'assistant-nav-toggle',
        'assistant-resize-n', 'assistant-resize-s', 'assistant-resize-e', 'assistant-resize-w', 'assistant-resize-nw', 'assistant-resize-ne', 'assistant-resize-sw', 'assistant-panel-header', 'assistant-panel-resize', 'assistant-panel-title', 'chat-input-box', 'master-brand-image-lightbox',
    ].map(id => [id, element(id)]));
    ids['dashboard-floating-assistant'].parentElement = ids['assistant-launcher-home'];
    ids['tab-chat'].hidden = true;
    ids['master-brand-image-lightbox'].hidden = true;
    ids['tab-chat'].contains = el => el === ids['chat-input-box'] || el === ids['assistant-panel-title'];
    const handlers = {};
    const originalFocus = element('dashboard-control');
    document = {
        activeElement: originalFocus,
        getElementById: id => ids[id],
        addEventListener: (name, handler) => { handlers[name] = handler; },
    };
    const localStorage = {getItem:key=>storage.get(key) ?? null, setItem:(key,value)=>storage.set(key,value)};
    const context = vm.createContext({ document, window, localStorage });
    vm.runInContext(block[1] + '\n' + dragBlock[1] + '\n' + (windowBlock?.[1] || ''), context);
    return { ids, handlers, document, originalFocus, context, pointerHandlers, windowHandlers, window, storage, elementHandlers };
}

test('floating toggle opens and closes without replacing chat draft or nodes', () => {
    const { ids, context } = setup();
    const input = ids['chat-input-box'];
    context.toggleDashboardAssistant();
    assert.equal(ids['tab-chat'].hidden, false);
    assert.equal(ids['dashboard-floating-assistant'].attributes['aria-expanded'], 'true');
    assert.equal(ids['assistant-nav-toggle'].attributes['aria-expanded'], 'true');
    context.toggleDashboardAssistant();
    assert.equal(ids['tab-chat'].hidden, true);
    assert.equal(ids['dashboard-floating-assistant'].attributes['aria-expanded'], 'false');
    assert.equal(input.value, 'draft stays here');
    assert.equal(ids['chat-input-box'], input);
    assert.equal(ids['dashboard-floating-assistant'].hidden, false);
});

test('nav and quick prompts always open instead of toggling closed', () => {
    const { ids, context, document } = setup();
    context.openDashboardAssistant();
    context.openDashboardAssistant();
    assert.equal(ids['tab-chat'].hidden, false);
    assert.equal(document.activeElement, ids['chat-input-box']);
});

test('close restores keyboard focus to the control that opened chat', () => {
    const { context, document, originalFocus } = setup();
    context.openDashboardAssistant();
    context.closeDashboardAssistant();
    assert.equal(document.activeElement, originalFocus);
});

test('Escape closes the panel and preserves the draft', () => {
    const { ids, context, handlers } = setup();
    context.openDashboardAssistant();
    let prevented = false;
    handlers.keydown({ key: 'Escape', defaultPrevented: false, preventDefault() { prevented = true; } });
    assert.equal(ids['tab-chat'].hidden, true);
    assert.equal(ids['chat-input-box'].value, 'draft stays here');
    assert.equal(prevented, true);
});

test('opening while a reply is pending focuses the assistant title', () => {
    const { ids, context, document } = setup();
    ids['chat-input-box'].disabled = true;
    context.openDashboardAssistant();
    assert.equal(document.activeElement, ids['assistant-panel-title']);
});

test('Escape leaves chat open while the image lightbox is on top', () => {
    const { ids, context, handlers } = setup();
    context.openDashboardAssistant();
    ids['master-brand-image-lightbox'].hidden = false;
    handlers.keydown({ key: 'Escape', defaultPrevented: false, preventDefault() {} });
    assert.equal(ids['tab-chat'].hidden, false);
});



function pointer(pointerId, clientX, clientY, extra = {}) {
    return {pointerId,clientX,clientY,button:0,isPrimary:true,preventDefault(){},...extra};
}

test('mouse drag moves and saves the launcher without toggling the chat', () => {
    const {ids,pointerHandlers,context,storage} = setup();
    const button = ids['dashboard-floating-assistant'];
    const start = button.getBoundingClientRect();
    pointerHandlers.pointerdown(pointer(1,start.left+30,start.top+20));
    pointerHandlers.pointermove(pointer(1,330,220));
    pointerHandlers.pointerup(pointer(1,330,220));
    const moved = button.getBoundingClientRect();
    assert.equal(moved.left,300);
    assert.equal(moved.top,200);
    assert.deepEqual(JSON.parse(storage.get('beviq_assistant_position')),{x:300,y:200});
    let suppressed=false;
    context.toggleDashboardAssistant({detail:1,preventDefault(){suppressed=true;}});
    assert.equal(suppressed,true);
    assert.equal(ids['tab-chat'].hidden,true);
    context.toggleDashboardAssistant({detail:1,preventDefault(){}});
    assert.equal(ids['tab-chat'].hidden,false);
});

test('small pointer jitter is a normal click rather than a drag', () => {
    const {ids,pointerHandlers,context,storage} = setup();
    pointerHandlers.pointerdown(pointer(1,1200,850));
    pointerHandlers.pointermove(pointer(1,1203,852));
    pointerHandlers.pointerup(pointer(1,1203,852));
    context.toggleDashboardAssistant({detail:1,preventDefault(){}});
    assert.equal(ids['tab-chat'].hidden,false);
    assert.equal(storage.has('beviq_assistant_position'),false);
});

test('drag clamps to screen edges and cancelled drag restores its original position', () => {
    const {ids,pointerHandlers,storage} = setup();
    const button=ids['dashboard-floating-assistant'];
    const original=button.getBoundingClientRect();
    pointerHandlers.pointerdown(pointer(1,original.left,original.top));
    pointerHandlers.pointermove(pointer(1,-5000,-5000));
    assert.equal(button.getBoundingClientRect().left,12);
    assert.equal(button.getBoundingClientRect().top,12);
    pointerHandlers.pointercancel(pointer(1,-5000,-5000));
    assert.equal(button.getBoundingClientRect().left,original.left);
    assert.equal(button.getBoundingClientRect().top,original.top);
    assert.equal(storage.has('beviq_assistant_position'),false);
});

test('saved position is restored and stays bounded after viewport resize', () => {
    const {ids,window,windowHandlers} = setup(JSON.stringify({x:1000,y:750}));
    const button=ids['dashboard-floating-assistant'];
    assert.equal(button.getBoundingClientRect().left,1000);
    assert.equal(button.getBoundingClientRect().top,750);
    window.innerWidth=360;
    window.innerHeight=640;
    windowHandlers.resize();
    const rect=button.getBoundingClientRect();
    assert.ok(rect.left>=12 && rect.right<=348);
    assert.ok(rect.top>=12 && rect.bottom<=628);
});

test('keyboard activation remains available immediately after a drag', () => {
    const {ids,pointerHandlers,context} = setup();
    pointerHandlers.pointerdown(pointer(1,1200,850));
    pointerHandlers.pointermove(pointer(1,200,200));
    pointerHandlers.pointerup(pointer(1,200,200));
    context.toggleDashboardAssistant({detail:0,preventDefault(){}});
    assert.equal(ids['tab-chat'].hidden,false);
});

test('invalid saved coordinates are ignored safely', () => {
    for (const value of ['not-json','{"x":"bad","y":null}','{"x":null,"y":5}']) {
        const {ids}=setup(value);
        assert.equal(ids['tab-chat'].hidden,true);
        assert.ok(Number.isFinite(ids['dashboard-floating-assistant'].getBoundingClientRect().left));
    }
});



test('full page chat clears floating coordinates and preserves draft when closed', () => {
    const { ids, context } = setup();
    const panel = ids['tab-chat'];
    panel.style.left = '500px';
    panel.style.top = '100px';
    panel.style.height = '240px';
    context.openAssistantPage();
    assert.equal(panel.hidden, false);
    assert.equal(panel.classList.contains('assistant-page'), true);
    assert.equal(panel.style.left, '');
    assert.equal(panel.style.top, '');
    assert.equal(panel.style.height, '');
    context.closeDashboardAssistant();
    assert.equal(panel.hidden, true);
    assert.equal(panel.classList.contains('assistant-page'), false);
    assert.equal(ids['chat-input-box'].value, 'draft stays here');
    context.toggleDashboardAssistant();
    assert.equal(panel.hidden, false);
    assert.equal(panel.classList.contains('assistant-page'), false);
});







test('page navigation hides the floating resize handle', () => {
    const { ids, context } = setup();
    context.openAssistantPage();
    assert.equal(ids['tab-chat'].hidden, false);
    assert.equal(ids['tab-chat'].classList.contains('assistant-page'), true);
    assert.equal(ids['assistant-panel-resize'].hidden, true);
});

test('dragging floating header moves the window independently of launcher', () => {
    const { ids, context, elementHandlers } = setup();
    context.toggleDashboardAssistant();
    const panel = ids['tab-chat'];
    const before = panel.getBoundingClientRect();
    const launcherBefore = ids['dashboard-floating-assistant'].getBoundingClientRect();
    const header = elementHandlers['assistant-panel-header'];
    assert.ok(header, 'Header drag handlers are required');
    header.pointerdown(pointer(4, before.left + 20, before.top + 20));
    header.pointermove(pointer(4, 60, 70));
    header.pointerup(pointer(4, 60, 70));
    assert.equal(panel.getBoundingClientRect().left, 40);
    assert.equal(panel.getBoundingClientRect().top, 50);
    assert.deepEqual(ids['dashboard-floating-assistant'].getBoundingClientRect(), launcherBefore);
    context.toggleDashboardAssistant();
    context.toggleDashboardAssistant();
    assert.deepEqual(panel.getBoundingClientRect(), {...before, left:40,top:50,right:40+before.width,bottom:50+before.height});
});

test('resize handle changes floating size and keeps it on screen after browser resize', () => {
    const { ids, context, elementHandlers, window, windowHandlers } = setup();
    context.toggleDashboardAssistant();
    const panel = ids['tab-chat'];
    const before = panel.getBoundingClientRect();
    const resize = elementHandlers['assistant-panel-resize'];
    assert.ok(resize, 'Resize handlers are required');
    resize.pointerdown(pointer(5, before.right, before.bottom));
    resize.pointermove(pointer(5, before.right - 120, before.bottom - 120));
    resize.pointerup(pointer(5, before.right - 120, before.bottom - 120));
    assert.equal(panel.getBoundingClientRect().width, before.width - 120);
    assert.equal(panel.getBoundingClientRect().height, before.height - 120);
    const resized = panel.getBoundingClientRect();
    context.toggleDashboardAssistant();
    context.toggleDashboardAssistant();
    assert.deepEqual(panel.getBoundingClientRect(), resized);
    window.innerWidth = 360;
    window.innerHeight = 520;
    windowHandlers.resize();
    const bounded = panel.getBoundingClientRect();
    assert.ok(bounded.left >= 12 && bounded.right <= 348);
    assert.ok(bounded.top >= 12 && bounded.bottom <= 508);
});

test('page to floating mode restores resize handle and previous floating position', () => {
    const { ids, context, elementHandlers } = setup();
    context.toggleDashboardAssistant();
    const panel = ids['tab-chat'];
    const before = panel.getBoundingClientRect();
    const header = elementHandlers['assistant-panel-header'];
    assert.ok(header);
    header.pointerdown(pointer(6, before.left, before.top));
    header.pointermove(pointer(6, 80, 90));
    header.pointerup(pointer(6, 80, 90));
    context.openAssistantPage();
    context.closeDashboardAssistant();
    context.toggleDashboardAssistant();
    assert.equal(panel.classList.contains('assistant-page'), false);
    assert.equal(ids['assistant-panel-resize'].hidden, false);
    assert.equal(panel.getBoundingClientRect().left, 80);
    assert.equal(panel.getBoundingClientRect().top, 90);
    assert.equal(ids['chat-input-box'].value, 'draft stays here');
});


test('all floating window edges resize while the opposite edge stays anchored', () => {
    for (const edge of ['n','s','e','w','nw','ne','sw']) {
        const { ids, context, elementHandlers } = setup();
        context.toggleDashboardAssistant();
        const panel = ids['tab-chat'];
        const before = panel.getBoundingClientRect();
        const resize = elementHandlers['assistant-resize-' + edge];
        assert.ok(resize, edge + ' edge must accept cursor dragging');
        const dx = edge.includes('w') ? 40 : edge.includes('e') ? -40 : 0;
        const dy = edge.includes('n') ? 30 : edge.includes('s') ? -30 : 0;
        resize.pointerdown(pointer(20, 500, 300));
        resize.pointermove(pointer(20, 500 + dx, 300 + dy));
        resize.pointerup(pointer(20, 500 + dx, 300 + dy));
        const after = panel.getBoundingClientRect();
        assert.equal(after.width, before.width - Math.abs(dx), edge);
        assert.equal(after.height, before.height - Math.abs(dy), edge);
        if (edge.includes('w')) assert.equal(after.right, before.right, edge);
        else assert.equal(after.left, before.left, edge);
        if (edge.includes('n')) assert.equal(after.bottom, before.bottom, edge);
        else assert.equal(after.top, before.top, edge);
    }
});

test('northwest resize respects minimum dimensions and cancellation restores bounds', () => {
    const { ids, context, elementHandlers } = setup();
    context.toggleDashboardAssistant();
    const panel = ids['tab-chat'];
    const before = panel.getBoundingClientRect();
    const resize = elementHandlers['assistant-resize-nw'];
    assert.ok(resize);
    resize.pointerdown(pointer(21,before.left,before.top));
    resize.pointermove(pointer(21,before.right+900,before.bottom+900));
    const after = panel.getBoundingClientRect();
    assert.equal(after.width,320);
    assert.equal(after.height,360);
    assert.equal(after.right,before.right);
    assert.equal(after.bottom,before.bottom);
    resize.pointercancel(pointer(21,before.right+900,before.bottom+900));
    assert.deepEqual(panel.getBoundingClientRect(),before);
});


test('floating close toggle docks in the chat header and returns home when closed', () => {
    const { ids, context, pointerHandlers } = setup();
    const launcher = ids['dashboard-floating-assistant'];
    context.toggleDashboardAssistant();
    assert.equal(launcher.parentElement, ids['assistant-panel-header']);
    assert.equal(launcher.classList.contains('assistant-launcher-docked'), true);
    pointerHandlers.pointerdown(pointer(30,100,100));
    assert.equal(launcher.hasPointerCapture(30), false);
    context.toggleDashboardAssistant();
    assert.equal(launcher.parentElement, ids['assistant-launcher-home']);
    assert.equal(launcher.classList.contains('assistant-launcher-docked'), false);
    assert.equal(ids['tab-chat'].hidden, true);
    assert.equal(ids['chat-input-box'].value, 'draft stays here');
});

test('full page assistant keeps the floating toggle outside its header', () => {
    const { ids, context } = setup();
    context.toggleDashboardAssistant();
    context.openAssistantPage();
    const launcher = ids['dashboard-floating-assistant'];
    assert.equal(launcher.parentElement, ids['assistant-launcher-home']);
    assert.equal(launcher.classList.contains('assistant-launcher-docked'), false);
    assert.equal(ids['tab-chat'].classList.contains('assistant-page'), true);
});
