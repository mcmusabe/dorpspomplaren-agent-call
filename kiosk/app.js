/**
 * De Dorpspomp & Dieks IJssalon - Voice Kiosk
 * VAPI Web SDK Integration - Script Tag Versie
 */

// ============================================
// DOM ELEMENTEN
// ============================================
const waveform = document.getElementById('waveform');
const statusText = document.getElementById('statusText');
const transcriptBox = document.getElementById('transcriptBox');
const callButton = document.getElementById('callButton');
const buttonIcon = document.getElementById('buttonIcon');
const buttonText = document.getElementById('buttonText');
const muteButton = document.getElementById('muteButton');
const orderItems = document.getElementById('orderItems');
const orderTotal = document.getElementById('orderTotal');
const assistantStatus = document.getElementById('assistantStatus');
const statusLabel = document.getElementById('statusLabel');

// ============================================
// STATE
// ============================================
let isCallActive = false;
let isMuted = false;
let transcriptMessages = [];
let currentOrder = [];
let orderTotalAmount = 0;
let vapiInitialized = false;
let listenersAttached = false;
const toolCallNameById = new Map();
const priceLookupCache = new Map();
const WEBHOOK_BASE_URL = 'https://dorpspomp-webhook.vercel.app';
let currentVapiCallId = null;
let cartSyncIntervalId = null;
const CART_SYNC_INTERVAL_MS = 1200;
const ASSISTANT_MERGE_WINDOW_MS = 6000;
const ASSISTANT_MAX_MERGED_LENGTH = 420;

function setCurrentVapiCallId(callId) {
    if (typeof callId !== 'string') return;
    const trimmed = callId.trim();
    if (!trimmed) return;
    currentVapiCallId = trimmed;
}

async function syncCartFromServer() {
    if (!isCallActive || !currentVapiCallId) return;
    try {
        const response = await fetch(`${WEBHOOK_BASE_URL}/tools/get_cart`, {
            headers: {
                'x-vapi-call-id': currentVapiCallId
            }
        });

        if (!response.ok) return;
        const data = await response.json();
        if (!Array.isArray(data?.items)) return;
        if (data.items.length === 0) return;
        updateOrderDisplay(data.items, Number(data.total || 0));
    } catch (error) {
        console.log('Cart sync failed:', error);
    }
}

function startCartSync() {
    stopCartSync();
    void syncCartFromServer();
    cartSyncIntervalId = setInterval(() => {
        void syncCartFromServer();
    }, CART_SYNC_INTERVAL_MS);
}

function stopCartSync() {
    if (cartSyncIntervalId) {
        clearInterval(cartSyncIntervalId);
        cartSyncIntervalId = null;
    }
}

// ============================================
// VAPI INITIALISATIE
// ============================================
function initVapi() {
    console.log('initVapi called, vapiSDK available:', !!window.vapiSDK);

    if (!window.vapiSDK) {
        console.error('VAPI SDK not loaded yet');
        addConnectionStatus('disconnected');
        statusText.textContent = 'SDK NIET GELADEN';
        return;
    }

    // Voorkom dubbele initialisatie (DOMContentLoaded + SDK onload)
    if (vapiInitialized && window.vapiInstance) {
        console.log('VAPI already initialized, skipping');
        return;
    }

    try {
        // SDK run methode - dit initialiseert de VAPI instance
        window.vapiInstance = window.vapiSDK.run({
            apiKey: API_KEY,
            assistant: ASSISTANT_ID,
            config: {
                hideButton: true,  // Verberg ingebouwde knop
                position: "bottom-right",
            }
        });

        console.log('VAPI instance created:', !!window.vapiInstance);

        // Setup event listeners
        setupEventListeners();

        // Update UI
        addConnectionStatus('connected');
        statusText.textContent = 'DRUK OP DE KNOP OM TE BESTELLEN';
        updateAssistantStatus('idle', 'Diek is klaar');
        vapiInitialized = true;

        console.log('VAPI initialized successfully');

    } catch (error) {
        console.error('Failed to initialize VAPI:', error);
        addConnectionStatus('disconnected');
        statusText.textContent = 'VERBINDING MISLUKT';
    }
}

// ============================================
// EVENT LISTENERS
// ============================================
function setupEventListeners() {
    const vapi = window.vapiInstance;
    if (!vapi) {
        console.error('No VAPI instance for event listeners');
        return;
    }

    if (listenersAttached) {
        console.log('Event listeners already attached, skipping');
        return;
    }

    console.log('Setting up event listeners...');

    // Call gestart
    vapi.on('call-start', (call) => {
        console.log('Call started');
        isCallActive = true;
        setCurrentVapiCallId(call?.id || call?.call?.id);
        toolCallNameById.clear();
        updateUI('active');
        clearTranscript();
        clearOrder();
        startCartSync();
        addSystemMessage('Gesprek gestart...');
        updateAssistantStatus('listening', 'Diek luistert...');
    });

    // Call beëindigd
    vapi.on('call-end', () => {
        console.log('Call ended');
        isCallActive = false;
        isMuted = false;
        currentVapiCallId = null;
        stopCartSync();
        updateUI('idle');
        addSystemMessage('Gesprek beëindigd');
        updateAssistantStatus('idle', 'Diek is klaar');
        updateMuteButton();
    });

    // Gebruiker begint te spreken
    vapi.on('speech-start', () => {
        console.log('User speech started');
        waveform.classList.add('active');
        updateAssistantStatus('listening', 'Luisteren...');
    });

    // Gebruiker stopt met spreken
    vapi.on('speech-end', () => {
        console.log('User speech ended');
        waveform.classList.remove('active');
        updateAssistantStatus('thinking', 'Diek denkt na...');
    });

    // Volume niveau voor waveform
    vapi.on('volume-level', (volume) => {
        updateWaveform(volume);
    });

    // Berichten verwerken
    vapi.on('message', (message) => {
        handleMessage(message);
    });

    // Error handling
    vapi.on('error', (error) => {
        console.error('VAPI Error:', error);
        showToast('Er ging iets mis. Probeer het opnieuw.', 'error', 4000);
        // Alleen terminal errors beëindigen de call
        const errorCode = error?.code || error?.type || '';
        if (errorCode === 'call-ended' || errorCode === 'transport-error' || !isCallActive) {
            isCallActive = false;
            stopCartSync();
            updateUI('idle');
            updateAssistantStatus('idle', 'Diek is klaar');
            setBodyState('idle');
        }
    });

    console.log('Event listeners setup complete');
    listenersAttached = true;
}

// ============================================
// MESSAGE HANDLING
// ============================================
function handleMessage(message) {
    console.log('Message received:', message.type, message);
    if (message?.call?.id) {
        setCurrentVapiCallId(message.call.id);
    }

    switch (message.type) {
        case 'transcript':
            handleTranscript(message);
            break;

        case 'tool-calls':
            handleToolCalls(message);
            break;

        case 'tool-call':
            handleToolCalls({ toolCalls: [message.toolCall || message] });
            break;

        case 'tool-call-result':
            handleToolCallResult(message);
            break;

        case 'function-call':
            handleFunctionCall(message);
            break;

        case 'function-call-result':
            handleFunctionCallResultMessage(message);
            break;

        case 'conversation-update':
            handleConversationUpdate(message);
            break;

        case 'speech-update':
            handleSpeechUpdate(message);
            break;

        case 'hang':
            addSystemMessage('🎉 Bedankt voor je bestelling!');
            break;

        case 'status-update':
            console.log('Status update:', message.status);
            break;

        default:
            if (message?.toolCallList || message?.toolCalls || message?.toolCall) {
                handleToolCalls(message);
            } else if (message?.functionCall) {
                handleFunctionCall(message);
            }
            break;
    }
}

function handleTranscript(message) {
    // VAPI stuurt role mee: 'user' of 'assistant'
    const role = message.role || 'user';
    
    if (message.transcriptType === 'partial') {
        // Partial assistant-transcript zorgt voor hakkelige/onjuiste tussenzinnen in de UI.
        if (role === 'user') {
            updatePartialTranscript(message.transcript, role);
        }
    } else if (message.transcriptType === 'final') {
        addTranscriptMessage(message.transcript, role);
    }
}

function handleToolCalls(message) {
    const calls = [];
    if (Array.isArray(message?.toolCalls)) {
        calls.push(...message.toolCalls);
    }
    if (Array.isArray(message?.toolCallList)) {
        calls.push(...message.toolCallList);
    }
    if (message?.toolCall) {
        calls.push(message.toolCall);
    }

    if (calls.length > 0) {
        calls.forEach(call => {
            const toolName = call.function?.name || call.name || 'onbekend';
            const toolCallId = call.id || call.toolCallId || call.functionCallId;
            const args = call.function?.arguments || call.arguments || {};
            console.log('Tool called:', toolName, args);

            if (toolCallId) {
                toolCallNameById.set(toolCallId, toolName);
            }

            // Parse arguments if string
            let parsedArgs = args;
            if (typeof args === 'string') {
                try { parsedArgs = JSON.parse(args); } catch(e) { parsedArgs = {}; }
            }

            switch (toolName) {
                case 'search_menu':
                    // Geen bericht - te langzaam
                    break;
                case 'add_to_cart':
                    // Voeg item direct toe aan lokale cart voor snelle UI update
                    const itemName = parsedArgs.item || parsedArgs.name || '';
                    const qty = Number(parsedArgs.quantity || 1);
                    if (itemName) {
                        addItemToLocalCart(itemName, Number.isFinite(qty) ? qty : 1);
                    }
                    break;
                case 'get_cart':
                    break;
                case 'send_order':
                    addSystemMessage('📤 Bestelling verzenden...');
                    break;
            }
        });
    }
}

// Lokale cart voor snelle UI updates
function addItemToLocalCart(itemName, quantity) {
    // Check of item al bestaat
    const existing = currentOrder.find(item => 
        item.name.toLowerCase() === itemName.toLowerCase()
    );
    
    if (existing) {
        existing.quantity += quantity;
    } else {
        // Voeg toe met geschatte prijs (wordt later geupdate)
        currentOrder.push({
            name: itemName,
            quantity: quantity,
            price: 0 // Prijs onbekend tot server response
        });
    }
    
    // Update display
    renderOrderDisplay();
    showToast(`${quantity}x ${itemName} toegevoegd!`, 'success', 2500);
    // Fallback: haal prijs direct op via webhook als VAPI result event ontbreekt
    void enrichLocalItemPrice(itemName);
    console.log('Cart updated:', currentOrder);
}

async function enrichLocalItemPrice(itemName) {
    const normalizedName = (itemName || '').toLowerCase().trim();
    if (!normalizedName) return;

    const cachedPrice = priceLookupCache.get(normalizedName);
    if (typeof cachedPrice === 'number' && cachedPrice > 0) {
        applyPriceToMatchingCartItem(itemName, itemName, cachedPrice);
        return;
    }

    try {
        const response = await fetch(`${WEBHOOK_BASE_URL}/tools/search_menu`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ query: itemName })
        });

        if (!response.ok) {
            return;
        }

        const data = await response.json();
        const items = Array.isArray(data?.items) ? data.items : [];
        if (items.length === 0) return;

        const best = findBestMenuMatch(normalizedName, items);
        if (!best || typeof best.price !== 'number' || best.price <= 0) {
            return;
        }

        priceLookupCache.set(normalizedName, best.price);
        applyPriceToMatchingCartItem(itemName, best.name || itemName, best.price);
    } catch (error) {
        console.log('Price lookup failed:', error);
    }
}

function findBestMenuMatch(normalizedName, menuItems) {
    let bestItem = null;
    let bestScore = -1;

    menuItems.forEach(item => {
        const candidateName = (item?.name || '').toLowerCase();
        if (!candidateName) return;

        let score = 0;
        if (candidateName === normalizedName) score = 100;
        else if (candidateName.includes(normalizedName) || normalizedName.includes(candidateName)) score = 80;
        else {
            const overlap = normalizedName.split(' ').filter(word => word && candidateName.includes(word)).length;
            score = overlap * 10;
        }

        if (score > bestScore) {
            bestScore = score;
            bestItem = item;
        }
    });

    return bestItem;
}

function applyPriceToMatchingCartItem(originalName, resolvedName, price) {
    const original = (originalName || '').toLowerCase();
    let updated = false;

    currentOrder.forEach(item => {
        const itemName = (item.name || '').toLowerCase();
        if (
            itemName === original ||
            itemName.includes(original) ||
            original.includes(itemName)
        ) {
            item.price = price;
            if (resolvedName) item.name = resolvedName;
            updated = true;
        }
    });

    if (updated) {
        orderTotalAmount = currentOrder.reduce((sum, item) => sum + (item.price * item.quantity), 0);
        renderOrderDisplay();
    }
}

function renderOrderDisplay() {
    if (!orderItems || !orderTotal) return;

    if (currentOrder.length === 0) {
        orderItems.innerHTML = '<li class="empty-order"><span class="empty-icon">🛒</span><span>Uw bestelling verschijnt hier</span></li>';
        orderTotal.textContent = '';
    } else {
        orderItems.innerHTML = currentOrder.map(item => {
            const priceDisplay = item.price > 0 
                ? formatEuroDisplay(item.price * item.quantity)
                : '';
            return `
                <li>
                    <span class="item-qty">${item.quantity}x</span>
                    <span class="item-name">${item.name}</span>
                    <span class="item-price">${priceDisplay}</span>
                </li>
            `;
        }).join('');
        
        const totalFromItems = currentOrder.reduce((sum, item) => sum + (item.price * item.quantity), 0);
        const total = orderTotalAmount > 0 ? orderTotalAmount : totalFromItems;
        orderTotal.textContent = total > 0 ? `Totaal: ${formatEuroDisplay(total)}` : 'Totaal: -';
    }
}

function handleToolCallResult(message) {
    const entries = extractToolResultEntries(message);
    if (entries.length === 0) {
        return;
    }

    entries.forEach(({ toolName, result }) => {
        console.log('Tool result received:', toolName, result);

        if (toolName === 'add_to_cart' && result) {
            if (result.cart && result.cart.items) {
                currentOrder = result.cart.items.map(item => ({
                    name: item.name,
                    quantity: item.qty || item.quantity || 1,
                    price: item.price || 0
                }));
                orderTotalAmount = Number(result.cart.total || 0);
                renderOrderDisplay();
            } else if (result.item) {
                const itemData = result.item;
                const existing = currentOrder.find(c =>
                    c.name.toLowerCase() === itemData.name.toLowerCase()
                );
                if (existing) {
                    existing.price = itemData.price || 0;
                    existing.name = itemData.name;
                }
                if (typeof result.total === 'number') {
                    orderTotalAmount = result.total;
                }
                renderOrderDisplay();
            }
        }

        if (toolName === 'search_menu' && result && result.items) {
            result.items.forEach(menuItem => {
                const cartItem = currentOrder.find(c =>
                    c.name.toLowerCase().includes(menuItem.name.toLowerCase()) ||
                    menuItem.name.toLowerCase().includes(c.name.toLowerCase())
                );
                if (cartItem && menuItem.price) {
                    cartItem.price = menuItem.price;
                    cartItem.name = menuItem.name;
                }
            });
            renderOrderDisplay();
        }

        if (toolName === 'get_cart' && result && result.items) {
            currentOrder = result.items.map(item => ({
                name: item.name,
                quantity: item.qty || item.quantity || 1,
                price: item.price || 0
            }));
            orderTotalAmount = Number(result.total || 0);
            renderOrderDisplay();
        }
    });
}

function extractToolResultEntries(message) {
    const entries = [];

    // Format 1: message.result + name/toolName
    if (message.result !== undefined) {
        entries.push({
            toolName: message.name || message.toolName || '',
            toolCallId: message.toolCallId || message.id,
            result: parseJsonIfNeeded(message.result)
        });
    }

    // Format 2: message.results = [{toolCallId, result}]
    if (Array.isArray(message.results)) {
        message.results.forEach(entry => {
            entries.push({
                toolName: entry.name || entry.toolName || '',
                toolCallId: entry.toolCallId || entry.id,
                result: parseJsonIfNeeded(entry.result)
            });
        });
    }

    // Format 3: nested object
    if (message.toolCallResult) {
        entries.push({
            toolName: message.toolCallResult.name || message.toolCallResult.toolName || '',
            toolCallId: message.toolCallResult.toolCallId || message.toolCallResult.id,
            result: parseJsonIfNeeded(message.toolCallResult.result)
        });
    }

    return entries.map(entry => {
        const resolvedName = entry.toolName || toolCallNameById.get(entry.toolCallId) || '';
        if (entry.toolCallId) {
            toolCallNameById.delete(entry.toolCallId);
        }
        return { toolName: resolvedName, result: entry.result };
    });
}

function parseJsonIfNeeded(value) {
    if (typeof value === 'string') {
        try {
            return JSON.parse(value);
        } catch (error) {
            return value;
        }
    }
    return value;
}

function handleFunctionCall(message) {
    const funcName = message.functionCall?.name;
    if (funcName) {
        console.log('Function called:', funcName);

        const args = parseJsonIfNeeded(message.functionCall?.arguments || {});
        if (funcName === 'add_to_cart' && args) {
            const itemName = args.item || args.name || '';
            const qty = Number(args.quantity || 1);
            if (itemName) {
                addItemToLocalCart(itemName, Number.isFinite(qty) ? qty : 1);
            }
        }

        if (message.functionCall?.result !== undefined) {
            handleToolCallResult({
                name: funcName,
                result: message.functionCall.result
            });
        } else if ((funcName === 'get_cart' || funcName === 'add_to_cart') && currentOrder.length === 0) {
            void syncCartFromServer();
        }
    }
}

function handleFunctionCallResultMessage(message) {
    const resultPayload = message.functionCallResult || message.functionCall || {};
    const funcName = resultPayload.name || message.name || message.toolName || '';
    const resultValue = resultPayload.result !== undefined ? resultPayload.result : message.result;

    if (!funcName || resultValue === undefined) {
        return;
    }

    handleToolCallResult({
        name: funcName,
        result: resultValue
    });
}

function handleConversationUpdate(message) {
    // Transcript events zijn al leidend; conversation-update zorgt anders voor duplicates.
    if (message.conversation && message.conversation.length > 0) {
        updateAssistantStatus('speaking', 'Diek spreekt...');
    }
}

function handleSpeechUpdate(message) {
    if (message.status === 'started' && message.role === 'assistant') {
        waveform.classList.add('active');
        updateAssistantStatus('speaking', 'Diek spreekt...');
    } else if (message.status === 'stopped') {
        waveform.classList.remove('active');
        updateAssistantStatus('listening', 'Diek luistert...');
    }
}

// ============================================
// CALL CONTROL
// ============================================
function toggleCall() {
    console.log('toggleCall, isCallActive:', isCallActive);

    if (isCallActive) {
        stopCall();
    } else {
        startCall();
    }
}

async function startCall() {
    const vapi = window.vapiInstance;

    if (!vapi) {
        console.error('VAPI not initialized, trying to init...');
        initVapi();
        return;
    }

    try {
        statusText.textContent = 'VERBINDEN...';
        updateAssistantStatus('connecting', 'Verbinden...');
        console.log('Starting call with assistant:', ASSISTANT_ID);

        // Script-tag SDK: start() met assistant ID
        const startedCall = await vapi.start(ASSISTANT_ID);
        setCurrentVapiCallId(startedCall?.id || startedCall?.call?.id);
        console.log('Call start command sent');

    } catch (error) {
        console.error('Failed to start call:', error);
        statusText.textContent = 'KON NIET VERBINDEN';
        updateAssistantStatus('error', 'Verbinding mislukt');
        setTimeout(() => {
            statusText.textContent = 'DRUK OP DE KNOP OM TE BESTELLEN';
            updateAssistantStatus('idle', 'Diek is klaar');
        }, 3000);
    }
}

function stopCall() {
    const vapi = window.vapiInstance;

    if (vapi && isCallActive) {
        console.log('Stopping call...');
        vapi.stop();
    }
}

// ============================================
// MUTE FUNCTIONALITEIT
// ============================================
function toggleMute() {
    const vapi = window.vapiInstance;

    if (!vapi || !isCallActive) {
        console.log('Cannot mute: no active call');
        return;
    }

    try {
        if (typeof vapi.isMuted === 'function') {
            isMuted = vapi.isMuted();
        }

        if (typeof vapi.setMuted === 'function') {
            vapi.setMuted(!isMuted);
            isMuted = !isMuted;
            updateMuteButton();

            if (isMuted) {
                addSystemMessage('🔇 Microfoon gedempt');
            } else {
                addSystemMessage('🔊 Microfoon actief');
            }
        }
    } catch (error) {
        console.error('Error toggling mute:', error);
    }
}

function updateMuteButton() {
    if (!muteButton) return;

    if (isMuted) {
        muteButton.classList.add('muted');
        muteButton.innerHTML = '<span>🔇</span><span>UNMUTE</span>';
    } else {
        muteButton.classList.remove('muted');
        muteButton.innerHTML = '<span>🔊</span><span>MUTE</span>';
    }
}

// ============================================
// UI UPDATES
// ============================================
function updateUI(state) {
    console.log('updateUI:', state);

    if (state === 'active') {
        callButton.classList.add('active');
        buttonIcon.textContent = '📞';
        buttonText.textContent = 'BEËINDIG GESPREK';
        statusText.textContent = 'LUISTEREN...';
        statusText.classList.add('active');
        waveform.classList.add('active');

        if (muteButton) muteButton.style.display = 'flex';
    } else {
        callButton.classList.remove('active');
        buttonIcon.textContent = '🎤';
        buttonText.textContent = 'START BESTELLING';
        statusText.textContent = 'DRUK OP DE KNOP OM TE BESTELLEN';
        statusText.classList.remove('active');
        waveform.classList.remove('active');

        if (muteButton) muteButton.style.display = 'none';
    }
}

function updateAssistantStatus(state, label) {
    if (!assistantStatus || !statusLabel) return;

    assistantStatus.classList.remove('idle', 'listening', 'speaking', 'thinking', 'connecting', 'error');
    assistantStatus.classList.add(state);
    statusLabel.textContent = label;
    setBodyState(state);
}

function setBodyState(state) {
    document.body.className = document.body.className.replace(/\bstate-\w+/g, '').trim();
    document.body.classList.add(`state-${state}`);
}

function showToast(message, type = 'info', durationMs = 3000) {
    const container = document.getElementById('toastContainer');
    if (!container) return;
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), durationMs);
}

function updateWaveform(volume) {
    const bars = waveform.querySelectorAll('.wave-bar');
    const normalizedVolume = Math.min(1, Math.max(0, volume));

    bars.forEach((bar, index) => {
        const centerIndex = bars.length / 2;
        const distanceFromCenter = Math.abs(index - centerIndex);
        const heightFactor = 1 - (distanceFromCenter / centerIndex) * 0.5;
        const randomFactor = 0.7 + Math.random() * 0.3;

        const height = 10 + (normalizedVolume * 50 * heightFactor * randomFactor);
        bar.style.height = `${height}px`;
    });
}

// ============================================
// TRANSCRIPT MANAGEMENT
// ============================================
function clearTranscript() {
    transcriptMessages = [];
    transcriptBox.innerHTML = '';
}

function addSystemMessage(text) {
    const messageEl = document.createElement('div');
    messageEl.className = 'transcript-message system';
    messageEl.innerHTML = `
        <div class="message-text system-text">
            ${text}
        </div>
    `;
    transcriptBox.appendChild(messageEl);
    scrollToBottom();
}

function normalizeTranscriptText(text) {
    return String(text || '')
        .replace(/\s+/g, ' ')
        .replace(/\s+([,.!?;:])/g, '$1')
        .trim();
}

function canonicalTranscriptText(text) {
    return normalizeTranscriptText(text)
        .toLowerCase()
        .replace(/[.,!?;:]/g, '')
        .trim();
}

function mergeAssistantText(previous, next) {
    if (!previous) return next;
    if (!next) return previous;
    if (previous === next || previous.includes(next)) return previous;
    if (next.startsWith(previous)) return next;

    const merged = `${previous} ${next}`
        .replace(/\s+/g, ' ')
        .replace(/\s+([,.!?;:])/g, '$1')
        .trim();
    return merged;
}

function formatEuroDisplay(value) {
    const amount = Number(value || 0);
    return `€${amount.toFixed(2).replace('.', ',')}`;
}

function addTranscriptMessage(text, role) {
    const partial = transcriptBox.querySelector('.partial-transcript');
    if (partial) partial.remove();

    const normalizedText = normalizeTranscriptText(text);
    if (!normalizedText) return;

    const lastMessage = transcriptMessages[transcriptMessages.length - 1];
    if (lastMessage && lastMessage.text === normalizedText && lastMessage.role === role) {
        return;
    }

    const now = Date.now();
    const normalizedCanonical = canonicalTranscriptText(normalizedText);
    if (
        lastMessage &&
        lastMessage.role === role &&
        (now - (lastMessage.timestamp || 0)) <= 3000 &&
        (
            normalizedText.startsWith(lastMessage.text) ||
            lastMessage.text.startsWith(normalizedText)
        )
    ) {
        const replacement = normalizedText.length >= lastMessage.text.length
            ? normalizedText
            : lastMessage.text;
        lastMessage.text = replacement;
        lastMessage.timestamp = now;
        if (lastMessage.element) {
            const textEl = lastMessage.element.querySelector('.message-text');
            if (textEl) {
                textEl.textContent = replacement;
            }
        }
        scrollToBottom();
        return;
    }

    if (
        role === 'assistant' &&
        lastMessage &&
        lastMessage.role === 'assistant' &&
        (now - (lastMessage.timestamp || 0)) <= ASSISTANT_MERGE_WINDOW_MS
    ) {
        const previousCanonical = canonicalTranscriptText(lastMessage.text);
        if (
            previousCanonical === normalizedCanonical ||
            previousCanonical.includes(normalizedCanonical) ||
            normalizedCanonical.includes(previousCanonical)
        ) {
            const replacement = normalizedText.length >= lastMessage.text.length
                ? normalizedText
                : lastMessage.text;
            lastMessage.text = replacement;
            lastMessage.timestamp = now;
            if (lastMessage.element) {
                const textEl = lastMessage.element.querySelector('.message-text');
                if (textEl) textEl.textContent = replacement;
            }
            scrollToBottom();
            return;
        }
    }

    if (
        role === 'assistant' &&
        lastMessage &&
        lastMessage.role === 'assistant' &&
        (now - (lastMessage.timestamp || 0)) <= ASSISTANT_MERGE_WINDOW_MS
    ) {
        const mergedText = mergeAssistantText(lastMessage.text, normalizedText);
        if (mergedText.length <= ASSISTANT_MAX_MERGED_LENGTH) {
            lastMessage.text = mergedText;
            lastMessage.timestamp = now;
            if (lastMessage.element) {
                const textEl = lastMessage.element.querySelector('.message-text');
                if (textEl) {
                    textEl.textContent = mergedText;
                }
            }
            scrollToBottom();
            return;
        }
    }

    transcriptMessages.push({ text: normalizedText, role, timestamp: now, element: null });

    const messageEl = document.createElement('div');
    messageEl.className = `transcript-message ${role}`;

    const label = role === 'user' ? 'Jij' : 'Diek';
    const icon = role === 'user' ? '👤' : '🤖';

    messageEl.innerHTML = `
        <div class="message-label">${icon} ${label}</div>
        <div class="message-text">${normalizedText}</div>
    `;

    const saved = transcriptMessages[transcriptMessages.length - 1];
    saved.element = messageEl;

    transcriptBox.appendChild(messageEl);
    scrollToBottom();
}

function updatePartialTranscript(text, role) {
    let partial = transcriptBox.querySelector('.partial-transcript');

    if (!partial) {
        partial = document.createElement('div');
        partial.className = `transcript-message ${role} partial-transcript`;
        transcriptBox.appendChild(partial);
    }

    const label = role === 'user' ? 'Jij' : 'Diek';
    const icon = role === 'user' ? '👤' : '🤖';

    partial.innerHTML = `
        <div class="message-label">${icon} ${label}</div>
        <div class="message-text">${text}<span class="typing-indicator">...</span></div>
    `;

    scrollToBottom();
}

function scrollToBottom() {
    transcriptBox.scrollTop = transcriptBox.scrollHeight;
}

// ============================================
// ORDER MANAGEMENT
// ============================================
function clearOrder() {
    currentOrder = [];
    orderTotalAmount = 0;
    renderOrderDisplay();
}

function updateOrderDisplay(items, total) {
    if (!orderItems || !orderTotal) return;

    currentOrder = (items || []).map(item => ({
        name: item.name,
        quantity: item.qty || item.quantity || 1,
        price: item.price || 0
    }));
    if (typeof total === 'number') {
        orderTotalAmount = total;
    } else {
        orderTotalAmount = currentOrder.reduce((sum, item) => sum + (item.price * item.quantity), 0);
    }

    if (currentOrder.length === 0) {
        orderItems.innerHTML = '<li class="empty-order"><span class="empty-icon">🛒</span><span>Uw bestelling verschijnt hier</span></li>';
        orderTotal.textContent = '';
    } else {
        orderItems.innerHTML = currentOrder.map(item => {
            const priceDisplay = item.price > 0
                ? formatEuroDisplay(item.price * item.quantity)
                : '';
            return `
            <li>
                <span class="item-qty">${item.quantity}x</span>
                <span class="item-name">${item.name}</span>
                <span class="item-price">${priceDisplay}</span>
            </li>
            `;
        }).join('');
    }

    orderTotal.textContent = orderTotalAmount > 0 ? `Totaal: ${formatEuroDisplay(orderTotalAmount)}` : '';
}

// ============================================
// CONNECTION STATUS
// ============================================
function addConnectionStatus(status) {
    const existing = document.querySelector('.connection-status');
    if (existing) existing.remove();

    const statusEl = document.createElement('div');
    statusEl.className = `connection-status ${status}`;
    statusEl.innerHTML = `
        <span class="status-dot"></span>
        <span>${status === 'connected' ? 'Verbonden' : 'Niet verbonden'}</span>
    `;
    document.body.appendChild(statusEl);
}

// ============================================
// INITIALISATIE
// ============================================
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded, vapiSDKLoaded:', window.vapiSDKLoaded);

    addConnectionStatus('disconnected');
    statusText.textContent = 'SDK LADEN...';

    if (muteButton) muteButton.style.display = 'none';

    if (window.vapiSDKLoaded) {
        console.log('SDK already loaded, initializing...');
        initVapi();
    }
});

window.addEventListener('beforeunload', () => {
    stopCartSync();
    const vapi = window.vapiInstance;
    if (vapi && isCallActive) {
        vapi.stop();
    }
});
