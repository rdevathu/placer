import { Link } from "react-router-dom";

export default function NotFoundPage() {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-2">
      <p className="text-[13px] font-semibold text-text">Page not found</p>
      <Link to="/patients" className="text-[12.5px] text-accent hover:underline">
        Back to patients
      </Link>
    </div>
  );
}
