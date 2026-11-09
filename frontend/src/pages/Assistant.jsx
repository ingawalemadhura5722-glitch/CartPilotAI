import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Bot, FlaskConical, Send, User } from "lucide-react";
import ProductCard from "../components/ProductCard.jsx";
import { getErrorMessage, sendChatMessage } from "../services/api.js";

const EXAMPLE_PROMPTS = [
  "Find me a laptop under ₹60,000 for programming.",
  "Suggest budget-friendly headphones.",
  "Best smartphone under ₹25,000",
  "Show me smart devices for my home",
];

const WELCOME = {
  id: 0,
  role: "assistant",
  text: "Hi! I'm the CartPilot demo assistant. Tell me what you're looking for and your budget, and I'll suggest products from our sample catalog.",
  products: [],
};

export default function Assistant() {
  const [searchParams] = useSearchParams();
  const [messages, setMessages] = useState([WELCOME]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const nextId = useRef(1);
  const bottomRef = useRef(null);
  const initialHandled = useRef(false);

  // Scroll to the newest message.
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, loading]);

  const sendMessage = async (text) => {
    const trimmed = text.trim();
    if (!trimmed || loading) return;

    setMessages((prev) => [...prev, { id: nextId.current++, role: "user", text: trimmed, products: [] }]);
    setInput("");
    setLoading(true);

    try {
      const data = await sendChatMessage(trimmed);
      setMessages((prev) => [
        ...prev,
        { id: nextId.current++, role: "assistant", text: data.reply, products: data.products },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { id: nextId.current++, role: "assistant", text: getErrorMessage(err), products: [], isError: true },
      ]);
    } finally {
      setLoading(false);
    }
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
                <small>Answers using the sample product catalog</small>
              </div>
            </div>
            <span className="demo-badge">
              <FlaskConical size={14} /> Demo assistant · not a real LLM
            </span>
          </header>

          <div className="chat-body" aria-live="polite">
            {messages.map((m) => (
              <div key={m.id} className={`msg ${m.role}`}>
                <span className={`avatar ${m.role === "user" ? "user" : "bot"}`}>
                  {m.role === "user" ? <User size={18} /> : <Bot size={18} />}
                </span>
                <div className="msg-content">
                  <div className={m.isError ? "bubble bubble-error" : "bubble"}>{m.text}</div>
                  {m.products.length > 0 && (
                    <div className="chat-products">
                      {m.products.map((p) => (
                        <ProductCard key={p.id} product={p} />
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}

            {loading && (
              <div className="msg assistant">
                <span className="avatar bot"><Bot size={18} /></span>
                <div className="bubble typing" aria-label="Assistant is typing">
                  <span /><span /><span />
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          <form className="chat-input" onSubmit={handleSubmit}>
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask for a product, e.g. phones under ₹25,000"
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
            <strong>How it works today</strong>
            <p>
              The backend looks for a budget, a category and a few keywords in your message, then
              ranks matching products. A real AI model will replace this in a later stage.
            </p>
          </div>
        </aside>
      </div>
    </div>
  );
}