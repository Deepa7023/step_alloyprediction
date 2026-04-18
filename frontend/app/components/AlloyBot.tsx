'use client';

import React, { useEffect, useMemo, useRef, useState } from 'react';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';
import { Bot, Send, X, Minimize2, Maximize2 } from 'lucide-react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || '';

interface Msg { role: 'user' | 'bot'; text: string; ts: number; }

const SUGGESTIONS = [
  'What did I upload?',
  'Explain my cost in simple words.',
  'Why was this alloy and machine selected?',
  'What should I change to reduce cost?',
];

const GENERAL_SUGGESTIONS = [
  'What CAD data can you read after upload?',
  'Which alloys work well for HPDC?',
  'How is HPDC die amortization calculated?',
  'Why does location affect metal cost?',
];

function BotAvatar({ speaking }: { speaking: boolean }) {
  return (
    <div className="bot-avatar pika-avatar" aria-hidden="true">
      <svg viewBox="0 0 100 112" width="60" height="60">
        <defs>
          <radialGradient id="pg-body" cx="45%" cy="35%" r="65%">
            <stop offset="0%" stopColor="#fff176" />
            <stop offset="100%" stopColor="#f9a825" />
          </radialGradient>
          <radialGradient id="pg-cheek" cx="40%" cy="40%" r="60%">
            <stop offset="0%" stopColor="#ff6d6d" />
            <stop offset="100%" stopColor="#d32f2f" />
          </radialGradient>
          <radialGradient id="pg-eye" cx="35%" cy="30%" r="70%">
            <stop offset="0%" stopColor="#4e2000" />
            <stop offset="100%" stopColor="#1a0800" />
          </radialGradient>
          <filter id="pg-glow" x="-25%" y="-25%" width="150%" height="150%">
            <feGaussianBlur stdDeviation="2" result="blur" />
            <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
          <filter id="pg-glow2" x="-40%" y="-40%" width="180%" height="180%">
            <feGaussianBlur stdDeviation="3.5" result="blur" />
            <feColorMatrix in="blur" type="matrix"
              values="1.2 0.6 0 0 0  0.9 0.5 0 0 0  0 0 0 0 0  0 0 0 1.4 0"
              result="cb" />
            <feMerge><feMergeNode in="cb" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
        </defs>

        {/* ── Ears ── */}
        <polygon points="18,40 8,4 36,26"  fill="#f9a825" />
        <polygon points="20,38 12,8  33,24" fill="#1a0800" />
        <polygon points="82,40 92,4 64,26"  fill="#f9a825" />
        <polygon points="80,38 88,8  67,24" fill="#1a0800" />

        {/* ── Body ── */}
        <ellipse cx="50" cy="78" rx="28" ry="22" fill="url(#pg-body)" filter="url(#pg-glow2)" />

        {/* ── Head ── */}
        <ellipse cx="50" cy="48" rx="33" ry="31" fill="url(#pg-body)" filter="url(#pg-glow2)" />

        {/* ── Back stripes ── */}
        <path d="M24 72 Q32 63 40 72" stroke="#b85c00" strokeWidth="2.5" fill="none" strokeLinecap="round" opacity="0.55" />
        <path d="M60 72 Q68 63 76 72" stroke="#b85c00" strokeWidth="2.5" fill="none" strokeLinecap="round" opacity="0.55" />

        {/* ── Eyes ── */}
        <ellipse cx="35" cy="44" rx="6"   ry="6.5" fill="url(#pg-eye)" />
        <ellipse cx="65" cy="44" rx="6"   ry="6.5" fill="url(#pg-eye)" />
        {/* shine dots */}
        <circle  cx="33" cy="41.5" r="2"  fill="white" opacity="0.95" />
        <circle  cx="63" cy="41.5" r="2"  fill="white" opacity="0.95" />
        {/* blink when speaking */}
        {speaking && (
          <>
            <ellipse cx="35" cy="44" rx="6" ry="6.5" fill="url(#pg-eye)">
              <animate attributeName="ry" values="6.5;0.8;6.5" dur="2.5s" repeatCount="indefinite" />
            </ellipse>
            <ellipse cx="65" cy="44" rx="6" ry="6.5" fill="url(#pg-eye)">
              <animate attributeName="ry" values="6.5;0.8;6.5" dur="2.5s" repeatCount="indefinite" />
            </ellipse>
          </>
        )}

        {/* ── Nose ── */}
        <ellipse cx="50" cy="55" rx="2.2" ry="1.5" fill="#3e1a00" />

        {/* ── Mouth ── */}
        {speaking ? (
          <path stroke="#3e1a00" strokeWidth="2.2" fill="#c62828" strokeLinecap="round"
            d="M43 59 Q50 67 57 59">
            <animate attributeName="d"
              values="M43 59 Q50 65 57 59;M43 60 Q50 69 57 60;M43 59 Q50 65 57 59"
              dur="0.5s" repeatCount="indefinite" />
          </path>
        ) : (
          <path d="M43 58 Q50 64 57 58" stroke="#3e1a00" strokeWidth="2.2" fill="none" strokeLinecap="round" />
        )}

        {/* ── Red cheeks ── */}
        <ellipse cx="22" cy="57" rx="8" ry="5.5" fill="url(#pg-cheek)" opacity="0.9" filter="url(#pg-glow)" />
        <ellipse cx="78" cy="57" rx="8" ry="5.5" fill="url(#pg-cheek)" opacity="0.9" filter="url(#pg-glow)" />
        {speaking && (
          <>
            <ellipse cx="22" cy="57" rx="11" ry="8" fill="#ff5252" opacity="0">
              <animate attributeName="opacity" values="0;0.4;0" dur="0.7s" repeatCount="indefinite" />
            </ellipse>
            <ellipse cx="78" cy="57" rx="11" ry="8" fill="#ff5252" opacity="0">
              <animate attributeName="opacity" values="0;0.4;0" dur="0.7s" repeatCount="indefinite" begin="0.15s" />
            </ellipse>
          </>
        )}

        {/* ── Arms ── */}
        <ellipse cx="17" cy="78" rx="8" ry="5" fill="#f9a825" transform="rotate(-35 17 78)" />
        <ellipse cx="83" cy="78" rx="8" ry="5" fill="#f9a825" transform="rotate(35 83 78)" />

        {/* ── Feet ── */}
        <ellipse cx="38" cy="99" rx="11" ry="7" fill="#f9a825" />
        <ellipse cx="62" cy="99" rx="11" ry="7" fill="#f9a825" />
        {/* toe lines */}
        <path d="M30 102 Q38 106 46 102" stroke="#e65100" strokeWidth="1.2" fill="none" opacity="0.5" />
        <path d="M54 102 Q62 106 70 102" stroke="#e65100" strokeWidth="1.2" fill="none" opacity="0.5" />

        {/* ── Lightning bolt tail (always visible) ── */}
        <g transform="translate(88,44)" filter="url(#pg-glow)">
          <polygon points="0,0 5,-8 3,-2 9,-10 4,2 8,-4 2,10" fill="#ffe033" stroke="#f9a825" strokeWidth="0.8" />
          {speaking && (
            <animate attributeName="opacity" values="1;0.4;1" dur="0.6s" repeatCount="indefinite" />
          )}
        </g>

        {/* ── Electric sparkles when speaking ── */}
        {speaking && (
          <>
            <circle cx="8" cy="28" r="3" fill="#fff176">
              <animate attributeName="opacity" values="0;1;0" dur="0.8s" repeatCount="indefinite" />
              <animate attributeName="r" values="2;4;2" dur="0.8s" repeatCount="indefinite" />
            </circle>
            <circle cx="92" cy="26" r="2.5" fill="#fff176">
              <animate attributeName="opacity" values="0;1;0" dur="1s" repeatCount="indefinite" begin="0.25s" />
              <animate attributeName="r" values="1.5;3.5;1.5" dur="1s" repeatCount="indefinite" begin="0.25s" />
            </circle>
            <circle cx="50" cy="10" r="2" fill="#fff176">
              <animate attributeName="opacity" values="0;1;0" dur="0.65s" repeatCount="indefinite" begin="0.1s" />
            </circle>
          </>
        )}
      </svg>
    </div>
  );
}

function PikaAvatar({ speaking }: { speaking: boolean }) {
  return (
    <div className="bot-avatar pika-avatar" aria-hidden="true">
      <svg className="pika-svg" viewBox="0 0 120 120" width="76" height="76">
        <defs>
          <radialGradient id="pikaBody" cx="42%" cy="30%" r="70%">
            <stop offset="0%" stopColor="#fff985" />
            <stop offset="58%" stopColor="#ffd338" />
            <stop offset="100%" stopColor="#f2a20b" />
          </radialGradient>
          <radialGradient id="pikaCheek" cx="38%" cy="36%" r="70%">
            <stop offset="0%" stopColor="#ff8d8d" />
            <stop offset="100%" stopColor="#e51f26" />
          </radialGradient>
          <radialGradient id="pikaEye" cx="34%" cy="28%" r="78%">
            <stop offset="0%" stopColor="#4a2308" />
            <stop offset="100%" stopColor="#120602" />
          </radialGradient>
          <filter id="pikaGlow" x="-35%" y="-35%" width="170%" height="170%">
            <feGaussianBlur stdDeviation="2.6" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        <g className={speaking ? 'pika-character speaking' : 'pika-character'}>
          <polygon points="25,47 12,4 45,30" fill="#ffd338" />
          <polygon points="26,42 16,8 40,28" fill="#201007" />
          <polygon points="95,47 108,4 75,30" fill="#ffd338" />
          <polygon points="94,42 104,8 80,28" fill="#201007" />
          <path d="M98 62 L113 52 L106 71 L117 71 L100 91 L105 75 L94 78 Z" fill="#ffe45d" stroke="#9a5b00" strokeWidth="2" filter="url(#pikaGlow)" />

          <ellipse cx="60" cy="78" rx="34" ry="30" fill="url(#pikaBody)" />
          <ellipse cx="60" cy="48" rx="39" ry="34" fill="url(#pikaBody)" />
          <path d="M33 78 Q42 68 50 78" stroke="#9a5b00" strokeWidth="3" fill="none" strokeLinecap="round" opacity="0.52" />
          <path d="M70 78 Q79 68 87 78" stroke="#9a5b00" strokeWidth="3" fill="none" strokeLinecap="round" opacity="0.52" />

          <ellipse cx="43" cy="45" rx="7" ry="8" fill="url(#pikaEye)" />
          <ellipse cx="77" cy="45" rx="7" ry="8" fill="url(#pikaEye)" />
          <circle cx="40.8" cy="41.8" r="2.3" fill="#fff" />
          <circle cx="74.8" cy="41.8" r="2.3" fill="#fff" />
          <ellipse cx="60" cy="55" rx="2.6" ry="1.8" fill="#2a1305" />
          <path className="pika-mouth" d="M50 61 Q60 70 70 61" stroke="#2a1305" strokeWidth="2.7" fill={speaking ? '#e53935' : 'none'} strokeLinecap="round" />
          <ellipse cx="31" cy="60" rx="10" ry="7" fill="url(#pikaCheek)" filter="url(#pikaGlow)" />
          <ellipse cx="89" cy="60" rx="10" ry="7" fill="url(#pikaCheek)" filter="url(#pikaGlow)" />

          <ellipse cx="28" cy="82" rx="9" ry="6" fill="#f4b321" transform="rotate(-28 28 82)" />
          <ellipse cx="92" cy="82" rx="9" ry="6" fill="#f4b321" transform="rotate(28 92 82)" />
          <ellipse cx="46" cy="104" rx="12" ry="7" fill="#f4b321" />
          <ellipse cx="74" cy="104" rx="12" ry="7" fill="#f4b321" />
        </g>

        {speaking && (
          <g className="pika-electric" filter="url(#pikaGlow)">
            <path d="M13 35 L21 29 L18 38 L26 35" stroke="#fff26a" strokeWidth="3" fill="none" strokeLinecap="round" />
            <path d="M100 33 L109 27 L105 38 L114 35" stroke="#fff26a" strokeWidth="3" fill="none" strokeLinecap="round" />
            <circle cx="60" cy="13" r="3" fill="#fff26a" />
          </g>
        )}
      </svg>
    </div>
  );
}

export default function AlloyBot({ reportContext }: { reportContext?: Record<string, any> | null }) {
  const [open, setOpen] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const hasFileContext = Boolean(reportContext?.file);
  const suggestions = useMemo(() => hasFileContext ? SUGGESTIONS : GENERAL_SUGGESTIONS, [hasFileContext]);
  const [messages, setMessages] = useState<Msg[]>(() => [
    { role: 'bot', text: "Hi, I'm AlloyBot. Upload a CAD file and I can explain the actual geometry, cost, assumptions, and market data from your quote.", ts: Date.now() },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, open]);

  const send = async (text?: string) => {
    const msg = (text || input).trim();
    if (!msg || loading) return;
    setInput('');
    setMessages((prev) => [...prev, { role: 'user', text: msg, ts: Date.now() }]);
    setLoading(true);
    try {
      const { data } = await axios.post(`${API_URL}/api/chat`, { message: msg, context: reportContext || undefined });
      setMessages((prev) => [...prev, { role: 'bot', text: data.reply, ts: Date.now() }]);
    } catch {
      setMessages((prev) => [...prev, { role: 'bot', text: 'Network error — please try again.', ts: Date.now() }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {/* Floating trigger */}
      <AnimatePresence>
        {!open && (
          <motion.button
            className="bot-trigger"
            onClick={() => setOpen(true)}
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0, opacity: 0 }}
            whileHover={{ scale: 1.08 }}
            whileTap={{ scale: 0.94 }}
            title="Open AlloyBot"
          >
            <PikaAvatar speaking={false} />
            <span className="bot-trigger-label">AlloyBot</span>
          </motion.button>
        )}
      </AnimatePresence>

      {/* Chat window */}
      <AnimatePresence>
        {open && (
          <motion.div
            className={`bot-window ${expanded ? 'bot-expanded' : ''} ${loading ? 'bot-thinking' : ''}`}
            initial={{ opacity: 0, y: 40, scale: 0.92 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 40, scale: 0.92 }}
            transition={{ type: 'spring', stiffness: 320, damping: 28 }}
          >
            {/* Header */}
            <div className="bot-header">
              <PikaAvatar speaking={loading} />
              <div>
                <strong>AlloyBot</strong>
                <span>{loading ? 'Reading your part data...' : hasFileContext ? `Using ${reportContext?.file}` : 'Waiting for uploaded CAD data'}</span>
              </div>
              <div className="bot-header-actions">
                <button type="button" onClick={() => setExpanded((e) => !e)} title={expanded ? 'Minimize' : 'Expand'}>
                  {expanded ? <Minimize2 size={15} /> : <Maximize2 size={15} />}
                </button>
                <button type="button" onClick={() => setOpen(false)} title="Close">
                  <X size={15} />
                </button>
              </div>
            </div>

            {/* Messages */}
            <div className="bot-messages">
              {hasFileContext && (
                <div className="bot-context-strip">
                  <strong>Part context active</strong>
                  <span>{reportContext?.file} · {reportContext?.market?.alloy?.replaceAll('_', ' ') || 'selected alloy'}</span>
                </div>
              )}
              {loading && <div className="bot-energy-field"><i /><i /><i /><i /><i /><i /></div>}
              {messages.map((m, i) => (
                <motion.div
                  key={i}
                  className={`bot-msg ${m.role}`}
                  initial={{ opacity: 0, x: m.role === 'user' ? 20 : -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.25 }}
                >
                  {m.role === 'bot' && <Bot size={14} className="msg-icon" />}
                  <span>{m.text}</span>
                </motion.div>
              ))}

              {loading && (
                <motion.div className="bot-msg bot typing-indicator" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                  <Bot size={14} className="msg-icon" />
                  <span className="typing-dots"><i /><i /><i /></span>
                </motion.div>
              )}
              <div ref={bottomRef} />
            </div>

            {/* Quick suggestions (only if no user messages yet) */}
            {messages.filter((m) => m.role === 'user').length === 0 && (
              <div className="bot-suggestions">
                {suggestions.map((s) => (
                  <button key={s} type="button" className="bot-suggestion" onClick={() => send(s)}>
                    {s}
                  </button>
                ))}
              </div>
            )}

            {/* Input */}
            <form
              className="bot-input-row"
              onSubmit={(e) => { e.preventDefault(); send(); }}
            >
              <input
                type="text"
                placeholder="Ask about alloys, HPDC costs…"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                disabled={loading}
                autoComplete="off"
              />
              <button type="submit" disabled={!input.trim() || loading} className="bot-send">
                <Send size={15} />
              </button>
            </form>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
