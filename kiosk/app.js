/**
 * Connect-Smart Voice Kiosk
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
        statusText.textContent = 'PLAATS JE BESTELLING ALS JE KLAAR BENT';
        updateAssistantStatus('idle', 'Lisa is klaar');

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

    console.log('Setting up event listeners...');

    // Call gestart
    vapi.on('call-start', () => {
        console.log('Call started');
        isCallActive = true;
        updateUI('active');
        clearTranscript();
        clearOrder();
        addSystemMessage('Gesprek gestart...');
        updateAssistantStatus('listening', 'Lisa luistert...');
    });

    // Call beëindigd
    vapi.on('call-end', () => {
        console.log('Call ended');
        isCallActive = false;
        isMuted = false;
        updateUI('idle');
        addSystemMessage('Gesprek beëindigd');
        updateAssistantStatus('idle', 'Lisa is klaar');
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
        updateAssistantStatus('thinking', 'Lisa denkt na...');
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
        addSystemMessage('Er is een fout opgetreden');
        isCallActive = false;
        updateUI('idle');
        updateAssistantStatus('error', 'Fout opgetreden');
    });

    console.log('Event listeners setup complete');
}

// ============================================
// MESSAGE HANDLING
// ============================================
function handleMessage(message) {
    console.log('Message received:', message.type, message);

    switch (message.type) {
        case 'transcript':
            handleTranscript(message);
            break;

        case 'tool-calls':
            handleToolCalls(message);
            break;

        case 'tool-call-result':
            handleToolCallResult(message);
            break;

        case 'function-call':
            handleFunctionCall(message);
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
    }
}

function handleTranscript(message) {
    // VAPI stuurt role mee: 'user' of 'assistant'
    const role = message.role || 'user';
    
    if (message.transcriptType === 'partial') {
        updatePartialTranscript(message.transcript, role);
    } else if (message.transcriptType === 'final') {
        addTranscriptMessage(message.transcript, role);
    }
}

function handleToolCalls(message) {
    if (message.toolCalls) {
        message.toolCalls.forEach(call => {
            const toolName = call.function?.name || call.name || 'onbekend';
            const args = call.function?.arguments || call.arguments || {};
            console.log('Tool called:', toolName, args);

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
                    const qty = parsedArgs.quantity || 1;
                    if (itemName) {
                        addItemToLocalCart(itemName, qty);
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
    console.log('Cart updated:', currentOrder);
}

function renderOrderDisplay() {
    if (!orderItems || !orderTotal) return;

    if (currentOrder.length === 0) {
        orderItems.innerHTML = '<li class="empty-order">Nog geen items</li>';
        orderTotal.textContent = 'Totaal: €0.00';
    } else {
        orderItems.innerHTML = currentOrder.map(item => {
            const priceDisplay = item.price > 0 
                ? `€${(item.price * item.quantity).toFixed(2)}` 
                : '';
            return `
                <li>
                    <span class="item-qty">${item.quantity}x</span>
                    <span class="item-name">${item.name}</span>
                    <span class="item-price">${priceDisplay}</span>
                </li>
            `;
        }).join('');
        
        // Bereken totaal alleen als we prijzen hebben
        const total = currentOrder.reduce((sum, item) => sum + (item.price * item.quantity), 0);
        orderTotal.textContent = total > 0 ? `Totaal: €${total.toFixed(2)}` : 'Totaal: -';
    }
}

function handleToolCallResult(message) {
    // VAPI stuurt tool results terug met name en result
    const toolName = message.name || message.toolName || '';
    let result = message.result;
    
    console.log('Tool result received:', toolName, result);
    
    // Parse result if string
    if (typeof result === 'string') {
        try { result = JSON.parse(result); } catch(e) { /* keep as string */ }
    }
    
    if (toolName === 'add_to_cart' && result) {
        console.log('Item toegevoegd:', result);
        
        // Als we cart data hebben van de server, gebruik die
        if (result.cart && result.cart.items) {
            currentOrder = result.cart.items.map(item => ({
                name: item.name,
                quantity: item.qty || item.quantity || 1,
                price: item.price || 0
            }));
            renderOrderDisplay();
        } 
        // Anders update het specifieke item met prijs
        else if (result.item) {
            const itemData = result.item;
            const existing = currentOrder.find(c => 
                c.name.toLowerCase() === itemData.name.toLowerCase()
            );
            if (existing) {
                existing.price = itemData.price || 0;
                existing.name = itemData.name; // Gebruik correcte naam van server
            }
            renderOrderDisplay();
        }
    }
    
    if (toolName === 'search_menu' && result && result.items) {
        // Update prijzen in lokale cart als we menu items krijgen
        result.items.forEach(menuItem => {
            const cartItem = currentOrder.find(c => 
                c.name.toLowerCase().includes(menuItem.name.toLowerCase()) ||
                menuItem.name.toLowerCase().includes(c.name.toLowerCase())
            );
            if (cartItem && menuItem.price) {
                cartItem.price = menuItem.price;
                cartItem.name = menuItem.name; // Gebruik correcte naam
            }
        });
        renderOrderDisplay();
    }
    
    if (toolName === 'get_cart' && result && result.items) {
        // Volledige cart van server - vervang lokale
        currentOrder = result.items.map(item => ({
            name: item.name,
            quantity: item.qty || item.quantity || 1,
            price: item.price || 0
        }));
        renderOrderDisplay();
    }
}

function handleFunctionCall(message) {
    const funcName = message.functionCall?.name;
    if (funcName) {
        console.log('Function called:', funcName);

        if (funcName === 'get_cart' && message.functionCall?.result) {
            try {
                const result = JSON.parse(message.functionCall.result);
                if (result.items) {
                    updateOrderDisplay(result.items, result.total);
                }
            } catch (e) {
                console.log('Could not parse cart result');
            }
        }
    }
}

function handleConversationUpdate(message) {
    if (message.conversation && message.conversation.length > 0) {
        const lastMessage = message.conversation[message.conversation.length - 1];
        if (lastMessage.role === 'assistant' && lastMessage.content) {
            addTranscriptMessage(lastMessage.content, 'assistant');
            updateAssistantStatus('speaking', 'Lisa spreekt...');
        }
    }
}

function handleSpeechUpdate(message) {
    if (message.status === 'started' && message.role === 'assistant') {
        waveform.classList.add('active');
        updateAssistantStatus('speaking', 'Lisa spreekt...');
    } else if (message.status === 'stopped') {
        waveform.classList.remove('active');
        updateAssistantStatus('listening', 'Lisa luistert...');
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
        await vapi.start(ASSISTANT_ID);
        console.log('Call start command sent');

    } catch (error) {
        console.error('Failed to start call:', error);
        statusText.textContent = 'KON NIET VERBINDEN';
        updateAssistantStatus('error', 'Verbinding mislukt');
        setTimeout(() => {
            statusText.textContent = 'PLAATS JE BESTELLING ALS JE KLAAR BENT';
            updateAssistantStatus('idle', 'Lisa is klaar');
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
        statusText.textContent = 'PLAATS JE BESTELLING ALS JE KLAAR BENT';
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

function addTranscriptMessage(text, role) {
    const partial = transcriptBox.querySelector('.partial-transcript');
    if (partial) partial.remove();

    if (!text || text.trim() === '') return;

    const lastMessage = transcriptMessages[transcriptMessages.length - 1];
    if (lastMessage && lastMessage.text === text && lastMessage.role === role) {
        return;
    }

    transcriptMessages.push({ text, role });

    const messageEl = document.createElement('div');
    messageEl.className = `transcript-message ${role}`;

    const label = role === 'user' ? 'Jij' : 'Lisa';
    const icon = role === 'user' ? '👤' : '🤖';

    messageEl.innerHTML = `
        <div class="message-label">${icon} ${label}</div>
        <div class="message-text">${text}</div>
    `;

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

    const label = role === 'user' ? 'Jij' : 'Lisa';
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
    orderTotalAmount = total || 0;

    if (currentOrder.length === 0) {
        orderItems.innerHTML = '<li class="empty-order">Nog geen items</li>';
    } else {
        orderItems.innerHTML = currentOrder.map(item => `
            <li>
                <span class="item-qty">${item.quantity}x</span>
                <span class="item-name">${item.name}</span>
                <span class="item-price">€${(item.price * item.quantity).toFixed(2)}</span>
            </li>
        `).join('');
    }

    orderTotal.textContent = `Totaal: €${orderTotalAmount.toFixed(2)}`;
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
    const vapi = window.vapiInstance;
    if (vapi && isCallActive) {
        vapi.stop();
    }
});
