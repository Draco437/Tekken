// TEKKEN BRAWL: OGRE VS PRINCESS - HTML5 / Web Port Engine
const canvas = document.getElementById('gameCanvas');
const ctx = canvas.getContext('2d');

const WIDTH = 960;
const HEIGHT = 540;
const FLOOR_Y = HEIGHT - 68;
const GRAVITY = 0.85;
const FRICTION = 0.80;

// Color Palette
const COLORS = {
    black: '#0a0810',
    white: '#ffffff',
    darkBg: '#0e0c16',
    darkPanel: '#161422',
    borderColor: '#2d2841',
    ogreGreen: '#00f078',
    ogreDark: '#008c46',
    princessPink: '#ff288c',
    princessDark: '#a00a50',
    gold: '#ffd21e',
    silver: '#b4b9c8',
    cyan: '#00e6ff',
    redDamage: '#ff3232',
    superOrange: '#ff8c00'
};

// -------------------------------------------------------------
// SOUND & AUDIO SYNTHESIZER (Web Audio API + TTS Announcer)
// -------------------------------------------------------------
let audioCtx = null;
let bgMusic = new Audio();
bgMusic.src = 'sounds/bg_music.mp3';
bgMusic.loop = true;
bgMusic.volume = 0.35;
let musicStarted = false;

function initAudio() {
    if (!audioCtx) {
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    }
    if (audioCtx.state === 'suspended') {
        audioCtx.resume();
    }
    if (!musicStarted) {
        bgMusic.play().then(() => { musicStarted = true; }).catch(() => {});
    }
}

function playSound(type) {
    if (!audioCtx) return;
    try {
        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();
        osc.connect(gain);
        gain.connect(audioCtx.destination);
        const t = audioCtx.currentTime;

        if (type === 'hit') {
            osc.type = 'sawtooth';
            osc.frequency.setValueAtTime(140, t);
            osc.frequency.exponentialRampToValueAtTime(30, t + 0.15);
            gain.gain.setValueAtTime(0.4, t);
            gain.gain.exponentialRampToValueAtTime(0.01, t + 0.15);
            osc.start(t);
            osc.stop(t + 0.15);
        } else if (type === 'super_hit') {
            osc.type = 'triangle';
            osc.frequency.setValueAtTime(320, t);
            osc.frequency.exponentialRampToValueAtTime(40, t + 0.35);
            gain.gain.setValueAtTime(0.7, t);
            gain.gain.exponentialRampToValueAtTime(0.01, t + 0.35);
            osc.start(t);
            osc.stop(t + 0.35);
        } else if (type === 'block') {
            osc.type = 'square';
            osc.frequency.setValueAtTime(480, t);
            osc.frequency.exponentialRampToValueAtTime(180, t + 0.1);
            gain.gain.setValueAtTime(0.3, t);
            gain.gain.exponentialRampToValueAtTime(0.01, t + 0.1);
            osc.start(t);
            osc.stop(t + 0.1);
        } else if (type === 'dash') {
            osc.type = 'sine';
            osc.frequency.setValueAtTime(260, t);
            osc.frequency.exponentialRampToValueAtTime(520, t + 0.12);
            gain.gain.setValueAtTime(0.25, t);
            gain.gain.exponentialRampToValueAtTime(0.01, t + 0.12);
            osc.start(t);
            osc.stop(t + 0.12);
        }
    } catch(e) {}
}

function speakAnnouncer(text) {
    if (!('speechSynthesis' in window)) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1.05;
    utterance.pitch = 0.85;
    
    const voices = window.speechSynthesis.getVoices();
    const enVoice = voices.find(v => v.lang.includes('en') && (v.name.includes('Male') || v.name.includes('David') || v.name.includes('Google')));
    if (enVoice) utterance.voice = enVoice;

    if (musicStarted) {
        bgMusic.volume = 0.12;
        utterance.onend = () => { bgMusic.volume = 0.35; };
    }
    window.speechSynthesis.speak(utterance);
}

// -------------------------------------------------------------
// SPRITE ASSET MANAGER
// -------------------------------------------------------------
const spriteCache = {};
const bgImg = new Image();
bgImg.src = 'Back.png';

function loadSprite(src) {
    if (!spriteCache[src]) {
        const img = new Image();
        img.src = src;
        spriteCache[src] = img;
    }
    return spriteCache[src];
}

const states = {
    idle: ['I1.png', 'I2.png'],
    walk: ['I1.png', 'I2.png'],
    attacking: ['A1.png', 'A2.png', 'A3.png'],
    jumping: ['J1.png', 'J2.png', 'J3.png'],
    blocking: ['B1.png'],
    hit: ['Da1.png'],
    defeated: ['D1.png'],
    super: ['A1.png', 'A2.png', 'A3.png']
};

['Images1', 'Images2'].forEach(charFolder => {
    ['Front', 'Back'].forEach(view => {
        Object.values(states).flat().forEach(file => {
            loadSprite(`${charFolder}/${view}/${file}`);
        });
    });
});

// -------------------------------------------------------------
// FIGHTER CLASS
// -------------------------------------------------------------
class Fighter {
    constructor(x, name, charType, primaryColor, controls, targetH = 150, playerNum = 1) {
        this.charType = charType;
        this.name = name;
        this.primaryColor = primaryColor;
        this.controls = controls;
        this.targetH = targetH;
        this.playerNum = playerNum;

        // Logical Push Box (body collision separate from sprite bounds)
        this.pushW = charType === 'princess' ? 52 : 60;
        this.pushH = targetH;
        this.x = x;
        this.y = FLOOR_Y - this.pushH;
        this.vx = 0;
        this.vy = 0;
        this.isJumping = false;

        this.maxHp = 100;
        this.hp = 100;
        this.displayHp = 100;
        this.superMeter = 0;
        this.maxSuper = 100;
        this.roundsWon = 0;

        this.state = 'idle';
        this.stateTimer = 0;
        this.comboCount = 0;
        this.comboTimer = 0;
        this.facing = playerNum === 1 ? 'right' : 'left';
        this.dashCooldown = 0;
        this.hasHitTarget = false;
        this.animFrame = 0.0;
        this.animSpeed = 0.09;

        this.folder = charType === 'ogre' ? 'Images1' : 'Images2';
    }

    get centerX() {
        return this.x + this.pushW / 2;
    }

    resetForRound(xPos) {
        this.x = xPos;
        this.y = FLOOR_Y - this.pushH;
        this.vx = 0;
        this.vy = 0;
        this.hp = this.maxHp;
        this.displayHp = this.maxHp;
        this.state = 'idle';
        this.stateTimer = 0;
        this.isJumping = false;
        this.dashCooldown = 0;
        this.hasHitTarget = false;
        this.animFrame = 0.0;
        this.facing = this.playerNum === 1 ? 'right' : 'left';
    }

    update(keys, opponent) {
        // 1. Stable Facing Direction (with 12px dead zone threshold)
        const centerDiff = opponent.centerX - this.centerX;
        if (Math.abs(centerDiff) > 12) {
            if (this.state !== 'dashing' && this.state !== 'super') {
                this.facing = centerDiff > 0 ? 'right' : 'left';
            }
        }

        if (this.dashCooldown > 0) this.dashCooldown--;

        if (this.comboTimer > 0) {
            this.comboTimer--;
            if (this.comboTimer === 0) this.comboCount = 0;
        }

        if (this.state !== 'dashing') {
            this.vx *= this.isJumping ? 0.94 : FRICTION;
        }

        // 2. Action State Timers
        if (this.stateTimer > 0) {
            this.stateTimer--;
            if (this.stateTimer === 0) {
                if (['attacking', 'hit', 'dashing', 'super'].includes(this.state)) {
                    this.state = 'idle';
                    this.animFrame = 0;
                    this.hasHitTarget = false;
                }
            }
        }

        // 3. Read Player Input Controls
        const isLeft = !!keys[this.controls.left];
        const isRight = !!keys[this.controls.right];
        const isJump = !!keys[this.controls.jump];
        const isBlock = !!keys[this.controls.block];

        // 4. Guard Logic
        if (this.state === 'blocking') {
            if (!isBlock) {
                this.state = 'idle';
                this.animFrame = 0;
            }
        }

        // 5. Movement and Jump Input Handling
        if (['idle', 'walk', 'jumping', 'blocking'].includes(this.state)) {
            if (isBlock && !this.isJumping) {
                if (this.state !== 'blocking') {
                    this.state = 'blocking';
                    this.animFrame = 0;
                }
                this.vx *= 0.82;
            } else {
                const speed = this.charType === 'princess' ? 6.0 : 5.4;

                // Handle simultaneous opposite inputs (Left + Right => 0)
                if (isLeft && isRight) {
                    this.vx = 0;
                } else if (isLeft) {
                    this.vx = -speed;
                } else if (isRight) {
                    this.vx = speed;
                }

                // Jump Trigger
                if (isJump && !this.isJumping) {
                    this.vy = -16.5;
                    this.isJumping = true;
                    this.state = 'jumping';
                    this.animFrame = 0;
                }
            }
        }

        // 6. Walk vs Idle State Transition
        if (!this.isJumping && ['idle', 'walk'].includes(this.state)) {
            if (Math.abs(this.vx) > 0.8) {
                if (this.state !== 'walk') {
                    this.state = 'walk';
                    this.animSpeed = 0.16;
                }
            } else {
                if (this.state !== 'idle') {
                    this.state = 'idle';
                    this.animFrame = 0;
                    this.animSpeed = 0.09;
                }
            }
        }

        // 7. Physics Integration
        this.x += this.vx;
        this.y += this.vy;

        if (this.y < FLOOR_Y - this.pushH) {
            this.vy += GRAVITY;
        } else {
            this.y = FLOOR_Y - this.pushH;
            this.vy = 0;
            this.isJumping = false;
            if (this.state === 'jumping') {
                this.state = Math.abs(this.vx) > 0.8 ? 'walk' : 'idle';
                this.animFrame = 0;
            }
        }

        // 8. Arena Screen Clamping
        const MIN_X = 30;
        const MAX_X = WIDTH - 30 - this.pushW;
        if (this.x < MIN_X) this.x = MIN_X;
        if (this.x > MAX_X) this.x = MAX_X;

        // 9. Smooth Health Lag
        if (this.displayHp > this.hp) {
            this.displayHp -= 0.6;
            if (this.displayHp < this.hp) this.displayHp = this.hp;
        }

        this.animFrame += this.animSpeed;
    }

    attack() {
        if (['idle', 'walk', 'jumping'].includes(this.state)) {
            this.state = 'attacking';
            this.stateTimer = 26;
            this.animFrame = 0;
            this.hasHitTarget = false;
            const lunge = this.charType === 'princess' ? 6 : 7;
            this.vx = this.facing === 'right' ? lunge : -lunge;
        }
    }

    superAttack() {
        if (this.superMeter >= this.maxSuper && ['idle', 'walk', 'jumping'].includes(this.state)) {
            this.superMeter = 0;
            this.state = 'super';
            this.stateTimer = 36;
            this.animFrame = 0;
            this.hasHitTarget = false;
            this.vx = this.facing === 'right' ? 14 : -14;
            playSound('dash');
            return true;
        }
        return false;
    }

    dash(keys, particles) {
        if (this.dashCooldown === 0 && ['idle', 'walk', 'jumping'].includes(this.state)) {
            let dir = 0;
            const isLeft = !!keys[this.controls.left];
            const isRight = !!keys[this.controls.right];

            if (isLeft && !isRight) dir = -1;
            else if (isRight && !isLeft) dir = 1;
            else dir = this.facing === 'right' ? 1 : -1;

            this.state = 'dashing';
            this.stateTimer = 12;
            this.animFrame = 0;
            this.vx = dir * 21;
            this.dashCooldown = 45;
            playSound('dash');

            for (let i = 0; i < 10; i++) {
                particles.push({
                    x: this.centerX + (Math.random() * 20 - 10),
                    y: this.y + this.pushH / 2 + (Math.random() * 40 - 20),
                    vx: (Math.random() - 0.5) * 6,
                    vy: (Math.random() - 0.5) * 4,
                    color: this.primaryColor,
                    alpha: 220,
                    size: Math.random() * 4 + 4
                });
            }
        }
    }

    draw(ctx) {
        const centerX = this.centerX;
        const altitude = Math.max(0, FLOOR_Y - (this.y + this.pushH));
        const shadowW = Math.max(16, (this.pushW + 30) * (1.0 - Math.min(0.7, altitude / 200)));
        const shadowH = Math.max(6, 10 * (1.0 - Math.min(0.7, altitude / 200)));

        // Ground Shadow
        ctx.fillStyle = 'rgba(10, 8, 14, 0.6)';
        ctx.beginPath();
        ctx.ellipse(centerX, FLOOR_Y, shadowW / 2, shadowH / 2, 0, 0, Math.PI * 2);
        ctx.fill();

        // Sprite Frame Selection
        const animFiles = states[this.state] || states.idle;
        let frameIdx = 0;

        if (this.state === 'jumping') {
            if (this.vy < -4) frameIdx = 0;
            else if (this.vy <= 4) frameIdx = Math.min(1, animFiles.length - 1);
            else frameIdx = Math.min(2, animFiles.length - 1);
        } else if (this.state === 'defeated') {
            const progress = 1.0 - Math.max(0, this.stateTimer) / 45;
            frameIdx = Math.min(Math.floor(progress * animFiles.length), animFiles.length - 1);
        } else if (['attacking', 'super', 'hit'].includes(this.state)) {
            const duration = this.state === 'super' ? 36 : (this.state === 'attacking' ? 26 : 20);
            const progress = 1.0 - Math.max(0, this.stateTimer / duration);
            frameIdx = Math.min(Math.floor(progress * animFiles.length), animFiles.length - 1);
        } else {
            frameIdx = Math.floor(this.animFrame) % animFiles.length;
        }

        const fileName = animFiles[frameIdx];
        const viewDir = 'Front';
        const spriteSrc = `${this.folder}/${viewDir}/${fileName}`;
        const sprite = loadSprite(spriteSrc);

        if (sprite && sprite.complete && sprite.naturalWidth > 0) {
            const scale = this.targetH / sprite.naturalHeight;
            const sprW = sprite.naturalWidth * scale;
            const sprH = this.targetH;

            // Stable Foot Alignment with Physics Position (lifts off floor during jump)
            let drawX = centerX - sprW / 2;
            const drawY = (this.y + this.pushH) - sprH;

            if (['attacking', 'super'].includes(this.state)) {
                const reachOffset = this.charType === 'princess' ? 14 : 18;
                drawX += this.facing === 'right' ? reachOffset : -reachOffset;
            }

            ctx.save();
            if (this.facing === 'left') {
                ctx.translate(centerX, 0);
                ctx.scale(-1, 1);
                ctx.translate(-centerX, 0);
            }
            ctx.drawImage(sprite, drawX, drawY, sprW, sprH);
            ctx.restore();
        }

        // Guard Barrier / Energy Shield Visual
        if (this.state === 'blocking') {
            ctx.save();
            const pulse = Math.sin(Date.now() * 0.012) * 0.15 + 0.85;
            const shieldX = this.facing === 'right' ? (this.x + this.pushW + 12) : (this.x - 12);
            const shieldY = this.y + this.pushH / 2;
            const radiusX = 24 * pulse;
            const radiusY = (this.pushH * 0.55) * pulse;

            // Outer Ambient Aura
            ctx.globalAlpha = 0.25 * pulse;
            ctx.fillStyle = this.primaryColor;
            ctx.beginPath();
            ctx.ellipse(shieldX, shieldY, radiusX + 14, radiusY + 14, 0, 0, Math.PI * 2);
            ctx.fill();

            // Core Forcefield Gradient
            const grad = ctx.createLinearGradient(
                this.facing === 'right' ? shieldX - radiusX : shieldX + radiusX, shieldY,
                this.facing === 'right' ? shieldX + radiusX : shieldX - radiusX, shieldY
            );
            grad.addColorStop(0, 'rgba(255, 255, 255, 0.15)');
            grad.addColorStop(0.5, this.primaryColor);
            grad.addColorStop(1, 'rgba(255, 255, 255, 0.9)');

            ctx.globalAlpha = 0.6 * pulse;
            ctx.fillStyle = grad;
            ctx.beginPath();
            ctx.ellipse(shieldX, shieldY, radiusX, radiusY, 0, 0, Math.PI * 2);
            ctx.fill();

            // Neon Outer Rim
            ctx.globalAlpha = 0.95 * pulse;
            ctx.strokeStyle = '#ffffff';
            ctx.lineWidth = 3;
            ctx.beginPath();
            ctx.ellipse(shieldX, shieldY, radiusX, radiusY, 0, 0, Math.PI * 2);
            ctx.stroke();

            // Inner Tech Energy Arc
            ctx.strokeStyle = this.primaryColor;
            ctx.lineWidth = 1.5;
            ctx.beginPath();
            ctx.ellipse(shieldX, shieldY, radiusX * 0.6, radiusY * 0.7, 0, 0, Math.PI * 2);
            ctx.stroke();

            ctx.restore();
        }
    }
}

// -------------------------------------------------------------
// PUSH BOX COLLISION RESOLUTION (PREVENT PASS-THROUGH)
// -------------------------------------------------------------
function resolveFighterBodyCollision(f1, f2) {
    // Check if either fighter is airborne high enough to cross over (cross-up jump)
    const f1Bottom = f1.y + f1.pushH;
    const f2Bottom = f2.y + f2.pushH;
    const f1Top = f1.y;
    const f2Top = f2.y;

    // Cross-up clearance: if one fighter is significantly higher than the other, allow aerial passage
    const isHighJumpCross = (f1Bottom < f2Top + 35) || (f2Bottom < f1Top + 35);
    if (isHighJumpCross) return;

    // Grounded or mid-body intersection: identify left and right fighters
    const leftFighter = f1.centerX <= f2.centerX ? f1 : f2;
    const rightFighter = f1.centerX <= f2.centerX ? f2 : f1;

    const overlap = (leftFighter.x + leftFighter.pushW) - rightFighter.x;

    if (overlap > 0) {
        // Resolve horizontal penetration symmetrically
        const halfOverlap = overlap / 2;
        leftFighter.x -= halfOverlap;
        rightFighter.x += halfOverlap;

        // Arena boundary enforcement with pushback
        const MIN_X = 30;
        const MAX_X = WIDTH - 30;

        if (leftFighter.x < MIN_X) {
            const wallPush = MIN_X - leftFighter.x;
            leftFighter.x = MIN_X;
            rightFighter.x = Math.min(MAX_X - rightFighter.pushW, rightFighter.x + wallPush);
        }
        if (rightFighter.x + rightFighter.pushW > MAX_X) {
            const wallPush = (rightFighter.x + rightFighter.pushW) - MAX_X;
            rightFighter.x = MAX_X - rightFighter.pushW;
            leftFighter.x = Math.max(MIN_X, leftFighter.x - wallPush);
        }

        // Final safety clamp so fighters never cross
        if (leftFighter.x + leftFighter.pushW > rightFighter.x) {
            rightFighter.x = leftFighter.x + leftFighter.pushW;
        }
    }
}

// -------------------------------------------------------------
// GAME CONTROLLER & REAL ELAPSED TIME CLOCK
// -------------------------------------------------------------
let p1, p2;
let gameState = 'menu';
let previousState = 'fight';
let roundNum = 1;

// --- AUTHORITATIVE MATCH CLOCK (REAL TIME, MONOTONIC) ---
const ROUND_DURATION_SECONDS = 99.0;
let matchTimeRemaining = ROUND_DURATION_SECONDS;
let timeOverHandled = false;
let lastPerfTimestamp = performance.now();

let introTimer = 0;
let roundBannerText = '';
let matchWinner = null;

let cameraShake = 0;
const particles = [];
const hitFlashes = [];

let p1Name = 'OGRE';
let p2Name = 'PRINCESS';

const keys = {};

// Handle Tab Visibility & Real-Time Sync
document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
        if (['fight', 'round_intro', 'round_over'].includes(gameState)) {
            previousState = gameState;
            gameState = 'paused';
            bgMusic.pause();
        }
    }
    lastPerfTimestamp = performance.now();
});

window.addEventListener('keydown', e => {
    initAudio();
    keys[e.code] = true;

    if (e.code === 'KeyP' || e.code === 'Escape') {
        if (['fight', 'round_intro', 'round_over'].includes(gameState)) {
            previousState = gameState;
            gameState = 'paused';
            bgMusic.pause();
        } else if (gameState === 'paused') {
            gameState = previousState;
            lastPerfTimestamp = performance.now();
            bgMusic.play().catch(() => {});
        }
    }

    if (gameState === 'fight') {
        // Player 1 Actions
        if (e.code === p1.controls.attack) p1.attack();
        if (e.code === p1.controls.dash) p1.dash(keys, particles);
        if (e.code === p1.controls.super) {
            if (p1.superAttack()) {
                speakAnnouncer('Super Move Unleashed!');
                cameraShake = 16;
            }
        }

        // Player 2 (Princess) Actions
        if (e.code === p2.controls.attack) p2.attack();
        if (e.code === p2.controls.dash) p2.dash(keys, particles);
        if (e.code === p2.controls.super) {
            if (p2.superAttack()) {
                speakAnnouncer('Super Move Unleashed!');
                cameraShake = 16;
            }
        }
    }

    if (gameState === 'match_over') {
        if (e.code === 'KeyR') {
            startNewMatch();
            speakAnnouncer('Rematch initiated! Fight!');
        } else if (e.code === 'KeyQ') {
            gameState = 'menu';
        }
    }
});

window.addEventListener('keyup', e => {
    keys[e.code] = false;
});

function initFighters() {
    const p1Binds = { left: 'KeyA', right: 'KeyD', jump: 'KeyW', block: 'KeyS', attack: 'KeyG', dash: 'ShiftLeft', super: 'KeyF' };
    const p2Binds = { left: 'ArrowLeft', right: 'ArrowRight', jump: 'ArrowUp', block: 'ArrowDown', attack: 'KeyL', dash: 'ControlRight', super: 'KeyK' };

    p1 = new Fighter(160, p1Name, 'ogre', COLORS.ogreGreen, p1Binds, 155, 1);
    p2 = new Fighter(WIDTH - 220, p2Name, 'princess', COLORS.princessPink, p2Binds, 145, 2);
}

function startNewMatch() {
    initFighters();
    roundNum = 1;
    matchWinner = null;
    startRound(1);
}

function startRound(rNum) {
    roundNum = rNum;
    p1.resetForRound(160);
    p2.resetForRound(WIDTH - 220);
    
    matchTimeRemaining = ROUND_DURATION_SECONDS;
    timeOverHandled = false;
    lastPerfTimestamp = performance.now();

    gameState = 'round_intro';
    introTimer = 90;

    if (roundNum === 3) {
        roundBannerText = 'FINAL ROUND';
        speakAnnouncer(`Final Round! ${p1.name} versus ${p2.name}! Fight for your life!`);
    } else {
        roundBannerText = `ROUND ${roundNum}`;
        speakAnnouncer(`Round ${roundNum}! ${p1.name} versus ${p2.name}! Fight!`);
    }
}

// -------------------------------------------------------------
// HIT DETECTION & COMBAT EVALUATION
// -------------------------------------------------------------
function processCombat(attacker, defender) {
    let shake = 0;
    const isSuper = attacker.state === 'super';
    const isAtk = attacker.state === 'attacking';

    if ((isAtk || isSuper) && !attacker.hasHitTarget) {
        const activeWindow = isAtk ? (attacker.stateTimer >= 4 && attacker.stateTimer <= 18) : (attacker.stateTimer >= 4 && attacker.stateTimer <= 28);
        if (activeWindow) {
            const reach = isSuper ? 90 : 75;
            // Overlap 10px into attacker body so close-contact attacks always connect
            const hx = attacker.facing === 'right' ? (attacker.x + attacker.pushW - 10) : (attacker.x - reach + 10);
            const hy = attacker.y + 20;

            const hitRect = { x: hx, y: hy, w: reach, h: 55 };
            const hurtRect = { x: defender.x + 4, y: defender.y + 4, w: defender.pushW - 8, h: defender.pushH - 8 };

            if (hitRect.x < hurtRect.x + hurtRect.w && hitRect.x + hitRect.w > hurtRect.x &&
                hitRect.y < hurtRect.y + hurtRect.h && hitRect.y + hitRect.h > hurtRect.y) {
                
                attacker.hasHitTarget = true;
                attacker.superMeter = Math.min(attacker.maxSuper, attacker.superMeter + (isSuper ? 15 : 22));

                if (defender.state === 'blocking') {
                    // Full protection against normal attacks, minor chip against super
                    const chipDamage = isSuper ? 4 : 0;
                    defender.hp = Math.max(0, defender.hp - chipDamage);
                    defender.vx = attacker.facing === 'right' ? (isSuper ? 12 : 8) : (isSuper ? -12 : -8);
                    shake = isSuper ? 6 : 3;
                    playSound('block');

                    // Shield Impact Flash Ring
                    hitFlashes.push({ x: attacker.facing === 'right' ? (defender.x - 5) : (defender.x + defender.pushW + 5), y: defender.y + defender.pushH / 2, r: 12, life: 8 });

                    // Shield Electric Sparks
                    for (let i = 0; i < 14; i++) {
                        particles.push({
                            x: defender.centerX,
                            y: defender.y + defender.pushH / 2,
                            vx: (Math.random() - 0.5) * 12,
                            vy: (Math.random() - 0.5) * 10,
                            color: COLORS.cyan,
                            alpha: 240,
                            size: Math.random() * 4 + 3
                        });
                    }
                } else {
                    defender.hp = Math.max(0, defender.hp - (isSuper ? 32 : 16));
                    defender.state = 'hit';
                    defender.stateTimer = 22;
                    defender.animFrame = 0;
                    defender.vx = attacker.facing === 'right' ? (isSuper ? 15 : 10) : (isSuper ? -15 : -10);
                    defender.vy = isSuper ? -5 : -2;
                    shake = isSuper ? 14 : 8;

                    playSound(isSuper ? 'super_hit' : 'hit');

                    attacker.comboCount++;
                    attacker.comboTimer = 60;

                    hitFlashes.push({ x: hx + reach / 2, y: hy + 25, r: 14, life: 10 });

                    const col = isSuper ? COLORS.gold : attacker.primaryColor;
                    for (let i = 0; i < (isSuper ? 16 : 12); i++) {
                        particles.push({
                            x: defender.centerX,
                            y: defender.y + defender.pushH / 2,
                            vx: (Math.random() - 0.5) * 14,
                            vy: -Math.random() * 8 - 1,
                            color: col,
                            alpha: 255,
                            size: Math.random() * 3 + 3
                        });
                    }
                }
            }
        }
    }
    return shake;
}

// -------------------------------------------------------------
// UI RENDERING
// -------------------------------------------------------------
function drawHUD() {
    const barW = 350, barH = 24, topY = 26;

    // P1 Health
    ctx.fillStyle = '#005028';
    ctx.fillRect(38, topY - 2, barW + 4, barH + 4);
    ctx.fillStyle = COLORS.black;
    ctx.fillRect(40, topY, barW, barH);
    if (p1.displayHp > 0) {
        ctx.fillStyle = COLORS.redDamage;
        ctx.fillRect(40, topY, barW * (p1.displayHp / p1.maxHp), barH);
    }
    if (p1.hp > 0) {
        ctx.fillStyle = COLORS.ogreGreen;
        ctx.fillRect(40, topY, barW * (p1.hp / p1.maxHp), barH);
    }

    ctx.fillStyle = COLORS.white;
    ctx.font = 'bold 20px Impact, sans-serif';
    ctx.fillText(p1.name, 40, topY + barH + 20);

    // P1 Round Orbs
    for (let i = 0; i < 2; i++) {
        ctx.beginPath();
        ctx.arc(190 + i * 22, topY + barH + 14, 7, 0, Math.PI * 2);
        ctx.fillStyle = p1.roundsWon > i ? COLORS.gold : COLORS.darkPanel;
        ctx.fill();
        ctx.strokeStyle = p1.roundsWon > i ? COLORS.white : COLORS.borderColor;
        ctx.stroke();
    }

    // P1 Super
    ctx.fillStyle = COLORS.darkPanel;
    ctx.fillRect(40, HEIGHT - 32, 220, 14);
    const sup1W = 220 * (p1.superMeter / p1.maxSuper);
    ctx.fillStyle = p1.superMeter >= p1.maxSuper ? COLORS.superOrange : COLORS.cyan;
    ctx.fillRect(40, HEIGHT - 32, sup1W, 14);
    ctx.fillStyle = p1.superMeter >= p1.maxSuper ? COLORS.gold : COLORS.silver;
    ctx.font = 'bold 12px Orbitron, monospace';
    ctx.fillText(p1.superMeter >= p1.maxSuper ? 'SUPER READY! [F]' : `SUPER ${Math.floor(p1.superMeter)}%`, 46, HEIGHT - 21);

    // P2 Health
    const p2X = WIDTH - 40 - barW;
    ctx.fillStyle = '#640032';
    ctx.fillRect(p2X - 2, topY - 2, barW + 4, barH + 4);
    ctx.fillStyle = COLORS.black;
    ctx.fillRect(p2X, topY, barW, barH);
    if (p2.displayHp > 0) {
        const rW = barW * (p2.displayHp / p2.maxHp);
        ctx.fillStyle = COLORS.redDamage;
        ctx.fillRect(p2X + barW - rW, topY, rW, barH);
    }
    if (p2.hp > 0) {
        const hpW = barW * (p2.hp / p2.maxHp);
        ctx.fillStyle = COLORS.princessPink;
        ctx.fillRect(p2X + barW - hpW, topY, hpW, barH);
    }

    ctx.fillStyle = COLORS.white;
    ctx.font = 'bold 20px Impact, sans-serif';
    const p2TextW = ctx.measureText(p2.name).width;
    ctx.fillText(p2.name, p2X + barW - p2TextW, topY + barH + 20);

    // P2 Round Orbs
    for (let i = 0; i < 2; i++) {
        ctx.beginPath();
        ctx.arc(p2X + barW - 170 - i * 22, topY + barH + 14, 7, 0, Math.PI * 2);
        ctx.fillStyle = p2.roundsWon > i ? COLORS.gold : COLORS.darkPanel;
        ctx.fill();
        ctx.strokeStyle = p2.roundsWon > i ? COLORS.white : COLORS.borderColor;
        ctx.stroke();
    }

    // P2 Super
    const sup2X = WIDTH - 40 - 220;
    ctx.fillStyle = COLORS.darkPanel;
    ctx.fillRect(sup2X, HEIGHT - 32, 220, 14);
    const sup2W = 220 * (p2.superMeter / p2.maxSuper);
    ctx.fillStyle = p2.superMeter >= p2.maxSuper ? COLORS.superOrange : COLORS.princessPink;
    ctx.fillRect(sup2X + 220 - sup2W, HEIGHT - 32, sup2W, 14);
    ctx.fillStyle = p2.superMeter >= p2.maxSuper ? COLORS.gold : COLORS.silver;
    ctx.font = 'bold 12px Orbitron, monospace';
    const sup2Txt = p2.superMeter >= p2.maxSuper ? 'SUPER READY! [K]' : `SUPER ${Math.floor(p2.superMeter)}%`;
    ctx.fillText(sup2Txt, sup2X + 220 - ctx.measureText(sup2Txt).width - 6, HEIGHT - 21);

    // Timer Box (Exact Real-Elapsed Seconds: Math.ceil gives 99 at 99.0s -> 98 at 98.0s -> 0 at 0.0s)
    ctx.fillStyle = COLORS.darkPanel;
    ctx.fillRect(WIDTH / 2 - 38, topY - 4, 76, 44);
    ctx.strokeStyle = COLORS.gold;
    ctx.lineWidth = 2;
    ctx.strokeRect(WIDTH / 2 - 38, topY - 4, 76, 44);
    
    const displaySeconds = Math.max(0, Math.ceil(matchTimeRemaining - 1e-4));
    ctx.fillStyle = displaySeconds <= 10 ? COLORS.redDamage : COLORS.white;
    ctx.font = 'bold 32px Orbitron, monospace';
    const timerStr = displaySeconds.toString().padStart(2, '0');
    ctx.fillText(timerStr, WIDTH / 2 - ctx.measureText(timerStr).width / 2, topY + 30);

    // Combos
    if (p1.comboCount > 1 && p1.comboTimer > 0) {
        ctx.fillStyle = COLORS.gold;
        ctx.font = 'bold 26px Orbitron, sans-serif';
        ctx.fillText(`${p1.comboCount} HITS!`, 40, topY + 80);
    }
    if (p2.comboCount > 1 && p2.comboTimer > 0) {
        ctx.fillStyle = COLORS.gold;
        ctx.font = 'bold 26px Orbitron, sans-serif';
        const txt = `${p2.comboCount} HITS!`;
        ctx.fillText(txt, p2X + barW - ctx.measureText(txt).width, topY + 80);
    }

    // Bottom Controls Guide
    ctx.fillStyle = 'rgba(14, 12, 22, 0.75)';
    ctx.fillRect(WIDTH / 2 - 280, HEIGHT - 18, 560, 16);
    ctx.fillStyle = COLORS.silver;
    ctx.font = '500 11px Orbitron, sans-serif';
    const hintTxt = 'P1: [A/D] Move [W] Jump [S] Shield [G] Attack [F] Super  |  P2: [←/→] Move [↑] Jump [↓] Shield [L] Attack [K] Super';
    ctx.fillText(hintTxt, WIDTH / 2 - ctx.measureText(hintTxt).width / 2, HEIGHT - 6);
}

// -------------------------------------------------------------
// MAIN GAME LOOP (FIXED TIMESTEP PHYSICS + REAL MONOTONIC CLOCK)
// -------------------------------------------------------------
initFighters();

canvas.addEventListener('click', e => {
    initAudio();
    const rect = canvas.getBoundingClientRect();
    const mx = (e.clientX - rect.left) * (WIDTH / rect.width);
    const my = (e.clientY - rect.top) * (HEIGHT / rect.height);

    if (gameState === 'menu') {
        if (mx >= WIDTH / 2 - 140 && mx <= WIDTH / 2 + 140 && my >= HEIGHT / 2 + 55 && my <= HEIGHT / 2 + 103) {
            startNewMatch();
        }
    }
});

const FIXED_TIMESTEP = 1 / 60;
let physicsAccumulator = 0;

function updatePhysicsStep() {
    if (['round_intro', 'fight', 'round_over', 'match_over'].includes(gameState)) {
        if (gameState === 'fight') {
            // Update fighter positions & states
            if (p1.state !== 'defeated') p1.update(keys, p2);
            else p1.stateTimer = Math.max(0, p1.stateTimer - 1);

            if (p2.state !== 'defeated') p2.update(keys, p1);
            else p2.stateTimer = Math.max(0, p2.stateTimer - 1);

            // Grounded Push-Box Collision Resolution (prevents passing through each other)
            resolveFighterBodyCollision(p1, p2);

            // Combat & Hit Resolution
            const s1 = processCombat(p1, p2);
            const s2 = processCombat(p2, p1);
            if (s1 > cameraShake) cameraShake = s1;
            if (s2 > cameraShake) cameraShake = s2;

            if (p1.hp <= 0 && p1.state !== 'defeated') {
                p1.hp = 0;
                p1.state = 'defeated';
                p1.stateTimer = 45;
                gameState = 'round_over';
                introTimer = 110;
                p2.roundsWon++;
                speakAnnouncer(`K.O.! ${p2.name} wins the round!`);
            } else if (p2.hp <= 0 && p2.state !== 'defeated') {
                p2.hp = 0;
                p2.state = 'defeated';
                p2.stateTimer = 45;
                gameState = 'round_over';
                introTimer = 110;
                p1.roundsWon++;
                speakAnnouncer(`K.O.! ${p1.name} wins the round!`);
            }
        }

        // Particle updates
        for (let i = particles.length - 1; i >= 0; i--) {
            const p = particles[i];
            p.x += p.vx;
            p.y += p.vy;
            p.vy += 0.35;
            p.alpha -= 7;
            if (p.alpha <= 0) {
                particles.splice(i, 1);
            }
        }

        // Hit flash updates
        for (let i = hitFlashes.length - 1; i >= 0; i--) {
            const f = hitFlashes[i];
            f.r += 7;
            f.life--;
            if (f.life <= 0) {
                hitFlashes.splice(i, 1);
            }
        }

        // Round Intro transition
        if (gameState === 'round_intro') {
            introTimer--;
            if (introTimer <= 0) {
                gameState = 'fight';
                lastPerfTimestamp = performance.now();
            }
        } else if (gameState === 'round_over') {
            introTimer--;
            if (introTimer <= 0) {
                if (p1.roundsWon >= 2) {
                    gameState = 'match_over';
                    matchWinner = p1;
                    speakAnnouncer(`${p1.name} is the ULTIMATE CHAMPION!`);
                } else if (p2.roundsWon >= 2) {
                    gameState = 'match_over';
                    matchWinner = p2;
                    speakAnnouncer(`${p2.name} is the ULTIMATE CHAMPION!`);
                } else {
                    startRound(roundNum + 1);
                }
            }
        }
    }
}

function gameLoop(currentTimestamp) {
    // 1. Calculate Real Elapsed Time
    const now = currentTimestamp || performance.now();
    let deltaSeconds = (now - lastPerfTimestamp) / 1000;
    lastPerfTimestamp = now;

    if (deltaSeconds > 0.1) deltaSeconds = 0.1;

    // 2. Authoritative Fight Clock Decrement (Real Time)
    if (gameState === 'fight' && matchTimeRemaining > 0) {
        matchTimeRemaining = Math.max(0, matchTimeRemaining - deltaSeconds);

        if (matchTimeRemaining <= 0 && !timeOverHandled) {
            timeOverHandled = true;
            matchTimeRemaining = 0;

            if (p1.hp > p2.hp) {
                p2.hp = 0;
                p2.state = 'defeated';
                p2.stateTimer = 45;
                gameState = 'round_over';
                introTimer = 110;
                p1.roundsWon++;
                speakAnnouncer(`TIME OVER! ${p1.name} wins on health!`);
            } else if (p2.hp > p1.hp) {
                p1.hp = 0;
                p1.state = 'defeated';
                p1.stateTimer = 45;
                gameState = 'round_over';
                introTimer = 110;
                p2.roundsWon++;
                speakAnnouncer(`TIME OVER! ${p2.name} wins on health!`);
            } else {
                p1.hp = 0;
                p2.hp = 0;
                p1.state = 'defeated';
                p2.stateTimer = 45;
                gameState = 'round_over';
                introTimer = 110;
                speakAnnouncer("TIME OVER! DRAW ROUND!");
            }
        }
    }

    // 3. Fixed-Step Physics Accumulator (120Hz/144Hz/240Hz monitor friendly)
    if (gameState !== 'paused') {
        physicsAccumulator += deltaSeconds;
        while (physicsAccumulator >= FIXED_TIMESTEP) {
            updatePhysicsStep();
            physicsAccumulator -= FIXED_TIMESTEP;
        }
    }

    // 4. Render Frame
    let shakeX = 0, shakeY = 0;
    if (cameraShake > 0) {
        shakeX = (Math.random() - 0.5) * cameraShake * 2;
        shakeY = (Math.random() - 0.5) * cameraShake * 2;
        if (gameState !== 'paused') cameraShake--;
    }

    ctx.save();
    ctx.translate(shakeX, shakeY);

    // Arena Backdrop
    if (bgImg && bgImg.complete && bgImg.naturalWidth > 0) {
        ctx.drawImage(bgImg, 0, 0, WIDTH, HEIGHT);
    } else {
        ctx.fillStyle = COLORS.darkBg;
        ctx.fillRect(0, 0, WIDTH, HEIGHT);
        ctx.fillStyle = '#1e1c2c';
        ctx.fillRect(0, FLOOR_Y, WIDTH, HEIGHT - FLOOR_Y);
    }

    // Menu State Render
    if (gameState === 'menu') {
        ctx.fillStyle = 'rgba(10, 8, 18, 0.85)';
        ctx.fillRect(0, 0, WIDTH, HEIGHT);

        ctx.fillStyle = COLORS.white;
        ctx.font = '900 68px Orbitron, sans-serif';
        const title = 'TEKKEN BRAWL';
        ctx.fillText(title, WIDTH / 2 - ctx.measureText(title).width / 2, HEIGHT / 2 - 80);

        ctx.fillStyle = COLORS.gold;
        ctx.font = '700 20px Rajdhani, sans-serif';
        const sub = 'OGRE  VS  PRINCESS : CHAMPIONSHIP ARENA';
        ctx.fillText(sub, WIDTH / 2 - ctx.measureText(sub).width / 2, HEIGHT / 2 - 20);

        // Start Button
        ctx.fillStyle = COLORS.darkPanel;
        ctx.fillRect(WIDTH / 2 - 140, HEIGHT / 2 + 55, 280, 48);
        ctx.strokeStyle = COLORS.ogreGreen;
        ctx.lineWidth = 2;
        ctx.strokeRect(WIDTH / 2 - 140, HEIGHT / 2 + 55, 280, 48);

        ctx.fillStyle = COLORS.white;
        ctx.font = 'bold 20px Orbitron, sans-serif';
        const btnTxt = 'ENTER TOURNAMENT';
        ctx.fillText(btnTxt, WIDTH / 2 - ctx.measureText(btnTxt).width / 2, HEIGHT / 2 + 86);
    }

    // Active Fight & Overlays Render
    else if (['round_intro', 'fight', 'round_over', 'match_over', 'paused'].includes(gameState)) {
        p1.draw(ctx);
        p2.draw(ctx);

        // Render Particles
        for (let i = 0; i < particles.length; i++) {
            const p = particles[i];
            ctx.fillStyle = p.color;
            ctx.globalAlpha = Math.max(0, p.alpha / 255);
            ctx.beginPath();
            ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
            ctx.fill();
            ctx.globalAlpha = 1.0;
        }

        // Render Hit Flashes
        for (let i = 0; i < hitFlashes.length; i++) {
            const f = hitFlashes[i];
            ctx.strokeStyle = 'rgba(255, 255, 255, 0.7)';
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.arc(f.x, f.y, f.r, 0, Math.PI * 2);
            ctx.stroke();
        }

        drawHUD();

        if (gameState === 'round_intro') {
            ctx.fillStyle = 'rgba(10, 8, 18, 0.5)';
            ctx.fillRect(0, 0, WIDTH, HEIGHT);

            ctx.fillStyle = COLORS.gold;
            ctx.font = '900 54px Orbitron, sans-serif';
            ctx.fillText(roundBannerText, WIDTH / 2 - ctx.measureText(roundBannerText).width / 2, HEIGHT / 2 - 20);

            ctx.fillStyle = COLORS.white;
            ctx.font = 'bold 28px Orbitron, sans-serif';
            const rdy = 'READY... FIGHT!';
            ctx.fillText(rdy, WIDTH / 2 - ctx.measureText(rdy).width / 2, HEIGHT / 2 + 30);
        } else if (gameState === 'round_over') {
            ctx.fillStyle = COLORS.redDamage;
            ctx.font = '900 70px Orbitron, sans-serif';
            const ko = 'K. O. !';
            ctx.fillText(ko, WIDTH / 2 - ctx.measureText(ko).width / 2, HEIGHT / 2);
        } else if (gameState === 'match_over') {
            ctx.fillStyle = 'rgba(10, 8, 18, 0.85)';
            ctx.fillRect(0, 0, WIDTH, HEIGHT);

            ctx.fillStyle = COLORS.gold;
            ctx.font = '900 48px Orbitron, sans-serif';
            const winTxt = `${matchWinner.name} VICTORIOUS!`;
            ctx.fillText(winTxt, WIDTH / 2 - ctx.measureText(winTxt).width / 2, HEIGHT / 2 - 40);

            ctx.fillStyle = COLORS.silver;
            ctx.font = 'bold 20px Orbitron, sans-serif';
            const resTxt = 'PRESS [R] FOR REMATCH | PRESS [Q] FOR MENU';
            ctx.fillText(resTxt, WIDTH / 2 - ctx.measureText(resTxt).width / 2, HEIGHT / 2 + 30);
        } else if (gameState === 'paused') {
            ctx.fillStyle = 'rgba(10, 8, 18, 0.8)';
            ctx.fillRect(0, 0, WIDTH, HEIGHT);

            ctx.fillStyle = COLORS.white;
            ctx.font = '900 48px Orbitron, sans-serif';
            const pTxt = 'GAME PAUSED';
            ctx.fillText(pTxt, WIDTH / 2 - ctx.measureText(pTxt).width / 2, HEIGHT / 2 - 20);

            ctx.fillStyle = COLORS.gold;
            ctx.font = '700 18px Orbitron, sans-serif';
            const pSub = 'PRESS [P] OR [ESC] TO RESUME';
            ctx.fillText(pSub, WIDTH / 2 - ctx.measureText(pSub).width / 2, HEIGHT / 2 + 30);
        }
    }

    ctx.restore();
    requestAnimationFrame(gameLoop);
}

// Start single authoritative game loop
requestAnimationFrame(gameLoop);
