import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { AlertTriangle, Bot, Eraser, Send, Sparkles, User } from "lucide-react";
import ProductCard from "../components/ProductCard.jsx";
import ComparisonTable from "../components/ComparisonTable.jsx";
import { getErrorMessage, sendChatMessage } from "../services/api.js";
import { formatPrice } from "../utils/format.js";

const EXAMPLE_PROMPTS = [
  "Find me a laptop under ₹60,000 for programming.",
  "Suggest wireless headphones under ₹3,000.",
  "I need a smartphone with a good camera.",
  "Compare the best two laptops.",
  "Find a budget-friendly smartwatch.",
];

const WELCOME = {
  id: 0,
  role: "assistant",
  isWelcome: true,
  text: "Hi! I'm CartPilot, your AI shopping assistant powered by Gemini. Tell me what you need, your budget and how you'll use it. I only recommend products that exist in our catalog, with real prices and stock.",
  products: [],
};

const MAX_HISTORY = 8; // how many earlier messages we send to the backend

// Build the history the backend expects (skips the welcome message and error bubbles).
function buildHistory(messages) {
  return messages
    .filter((m) => !m.isWelcome && !m.isError)
    .slice(-MAX_HISTORY)
    .map((m) => ({
      role: m.role,
      text: m.text.slice(0, 1000),
      product_ids: m.role === "assistant" ? m.products.map((p) => p.id).slice(0, 6) : [],
    }));
}

// Small chips that show what the AI understood from the message.
function intentChips(intent) {
  if (!intent) return [];
  const chips = [];
  if (intent.category) chips.push(intent.category);
  if (intent.min_budget && intent.max_budget) {
    chips.push(`${formatPrice(intent.min_budget)} – ${formatPrice(intent.max_budget)}`);
  } else if (intent.max_budget) {
    chips.push(`Under ${formatPrice(intent.max_budget)}`);
  } else if (intent.min_budget) {
    chips.push(`Above ${formatPrice(intent.min_budget)}`);
  }
  (intent.brands || []).forEach((b) => chips.push(b));
  if (intent.usage) chips.push(`For ${intent.usage}`);
  (intent.features || []).slice(0, 3).forEach((f) => chips.push(f));
  return chips;
}

export default function Assistant() {
  const [searchParams] = useSearchParams();
  const [messages, setMessages] = useState([WELCOME]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [suggestions, setSuggestions] = useState(EXAMPLE_PROMPTS.slice(0, 3));
  const nextId = useRef(1);
  const chatVersion = useRef(0); // lets us ignore replies that arrive after "Clear chat"
  const bottomRef = useRef(null);
  const initialHandled = useRef(false);

  // Scroll to the newest message.
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, loading]);

  const sendMessage = async (text) => {
    const trimmed = text.trim();
    if (!trimmed || loading) return;

    const history = buildHistory(messages); // messages BEFORE this new one
    const version = chatVersion.current;

    setMessages((prev) => [...prev, { id: nextId.current++, role: "user", text: trimmed, products: [] }]);
    setInput("");
    setLoading(true);

    try {
      const data = await sendChatMessage(trimmed, history);
      if (version !== chatVersion.current) return; // chat was cleared meanwhile
      setMessages((prev) => [
        ...prev,
        {
          id: nextId.current++,
          role: "assistant",
          text: data.reply,
          products: data.products || [],
          comparison: data.comparison || null,
          intent: data.intent || null,
          warning: data.warning || null,
        },
      ]);
      setSuggestions(data.suggestions?.length ? data.suggestions : EXAMPLE_PROMPTS.slice(0, 3));
    } catch (err) {
      if (version !== chatVersion.current) return;
      setMessages((prev) => [
        ...prev,
        { id: nextId.current++, role: "assistant", text: getErrorMessage(err), products: [], isError: true },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const clearChat = () => {
    chatVersion.current += 1;
    nextId.current = 1;
    setMessages([WELCOME]);
    setSuggestions(EXAMPLE_PROMPTS.slice(0, 3));
    setInput("");
    setLoading(false);
  };

  // If we arrived from the Home search (?q=...), send that question automatically (once).
  useEffect(() => {
    const q = searchParams.get("q");
    if (q && !initialHandled.current) {
      initialHandled.current = true;
      sendMessage(q);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSubmit = (event) => {
    event.preventDefault();
    sendMessage(input);
  };

  return (
    <div className="container page">
      <div className="assistant-layout">
        <section className="chat-card">
          <header className="chat-header">
            <div className="chat-title">
              <span className="avatar bot"><Bot size={20} /></span>
              <div>
                <strong>CartPilot Assistant</strong>
                <small>Recommendations come from our product database</small>
              </div>
            </div>
            <div className="chat-actions">
              <span className="ai-badge">
                <Sparkles size={14} /> Powered by Gemini
              </span>
              <button
                className="btn btn-outline btn-sm"
                onClick={clearChat}
                disabled={messages.length <= 1 && !loading}
              >
                <Eraser size={15} /> Clear chat
              </button>
            </div>
          </header>

          <div className="chat-body" aria-live="polite">
            {messages.map((m) => {
              const chips = m.role === "assistant" && !m.isError ? intentChips(m.intent) : [];
              return (
                <div key={m.id} className={`msg ${m.role}`}>
                  <span className={`avatar ${m.role === "user" ? "user" : "bot"}`}>
                    {m.role === "user" ? <User size={18} /> : <Bot size={18} />}
                  </span>
                  <div className="msg-content">
                    <div className={m.isError ? "bubble bubble-error" : "bubble"}>{m.text}</div>

                    {m.warning && (
                      <div className="msg-warning">
                        <AlertTriangle size={15} /> <span>{m.warning}</span>
                      </div>
                    )}

                    {chips.length > 0 && (
                      <div className="intent-chips" aria-label="What I understood">
                        {chips.map((chip) => (
                          <span key={chip} className="intent-chip">{chip}</span>
                        ))}
                      </div>
                    )}

                    {m.comparison ? (
                      <ComparisonTable comparison={m.comparison} products={m.products} />
                    ) : (
                      m.products.length > 0 && (
                        <div className="chat-products">
                          {m.products.map((p) => (
                            <ProductCard key={p.id} product={p} />
                          ))}
                        </div>
                      )
                    )}
                  </div>
                </div>
              );
            })}

            {loading && (
              <div className="msg assistant">
                <span className="avatar bot"><Bot size={18} /></span>
                <div className="bubble typing" aria-label="Gemini is thinking">
                  <span /><span /><span />
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {suggestions.length > 0 && (
            <div className="suggestion-chips" aria-label="Suggested questions">
              {suggestions.map((s) => (
                <button key={s} className="suggestion-chip" onClick={() => sendMessage(s)} disabled={loading}>
                  {s}
                </button>
              ))}
            </div>
          )}

          <form className="chat-input" onSubmit={handleSubmit}>
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask for a product, or compare options..."
              maxLength={500}
              aria-label="Message"
            />
            <button type="submit" className="btn btn-primary" disabled={loading || !input.trim()}>
              <Send size={16} /> Send
            </button>
          </form>
        </section>

        <aside className="side-card">
          <h3>Try an example</h3>
          <p>Click a prompt to send it to the assistant.</p>
          <div className="prompt-list">
            {EXAMPLE_PROMPTS.map((prompt) => (
              <button key={prompt} className="prompt-btn" onClick={() => sendMessage(prompt)} disabled={loading}>
                {prompt}
              </button>
            ))}
          </div>
          <div className="side-note">
            <strong>How it works</strong>
            <p>
              Gemini works out what you want. Our database finds real products. Gemini then explains them.
              Prices, ratings and stock always come from the database, never from the AI.
            </p>
          </div>
        </aside>
      </div>
    </div>
  );
}