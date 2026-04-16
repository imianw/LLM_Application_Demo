import { ChatPanel } from "./components/ChatPanel";

function App() {
  return (
    <main className="app-shell">
      <div className="backdrop backdrop-left" />
      <div className="backdrop backdrop-right" />
      <ChatPanel />
    </main>
  );
}

export default App;
