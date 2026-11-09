import { Loader2 } from "lucide-react";

export default function LoadingState({ label = "Loading..." }) {
  return (
    <div className="state-box">
      <Loader2 className="spinner" size={30} />
      <p>{label}</p>
    </div>
  );
}