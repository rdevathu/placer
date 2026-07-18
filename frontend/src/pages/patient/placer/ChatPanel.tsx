import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import clsx from "clsx";
import { SendHorizontal } from "lucide-react";
import { placerApi } from "../../../lib/api";
import { Card, CenteredSpinner, ErrorState } from "../../../components/ui";
import { formatDate } from "../../../lib/format";
import { errorMessage, useToast } from "../../../lib/toast";

export function ChatPanel({ patientId }: { patientId: string }) {
  const qc = useQueryClient();
  const toast = useToast();
  const [text, setText] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["placer-messages", patientId],
    queryFn: () => placerApi.listMessages(patientId),
    refetchInterval: 4000,
  });

  // Keep the newest message in view as messages arrive.
  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [data?.length]);

  const mutation = useMutation({
    mutationFn: (body: string) =>
      placerApi.sendMessage(patientId, { sender: "provider", sender_name: "Provider", text: body }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["placer-messages", patientId] });
      setText("");
    },
    onError: (err) => toast.error(errorMessage(err)),
  });

  const send = () => {
    const trimmed = text.trim();
    if (!trimmed || mutation.isPending) return;
    mutation.mutate(trimmed);
  };

  return (
    <Card className="flex h-[480px] flex-col lg:h-[calc(100vh-220px)] lg:min-h-[360px]">
      <div className="border-b border-border px-4 py-2.5">
        <h3 className="text-[12.5px] font-semibold text-text">Placer chat</h3>
        <p className="mt-0.5 text-[11.5px] text-text-tertiary">Message Placer about this patient</p>
      </div>

      <div ref={scrollRef} className="flex-1 overflow-y-auto px-3 py-3">
        {isLoading && <CenteredSpinner />}
        {isError && <ErrorState message={errorMessage(error)} />}
        {!isLoading && !isError && (!data || data.length === 0) && (
          <p className="px-1 py-8 text-center text-[12px] text-text-tertiary">
            No messages yet — Placer will post updates here.
          </p>
        )}
        <div className="flex flex-col gap-2.5">
          {data?.map((m) => {
            const fromPlacer = m.sender === "placer";
            return (
              <div key={m.id} className={clsx("flex flex-col", fromPlacer ? "items-start" : "items-end")}>
                <div
                  className={clsx(
                    "max-w-[85%] rounded-lg px-2.5 py-1.5 text-[12.5px] leading-relaxed",
                    fromPlacer ? "bg-accent-soft text-text" : "bg-bg-inset text-text",
                  )}
                >
                  <p className="whitespace-pre-wrap break-words">{m.text}</p>
                </div>
                <span className="mt-0.5 px-0.5 text-[10.5px] text-text-tertiary">
                  {fromPlacer ? m.sender_name ?? "Placer" : m.sender_name ?? "Provider"} ·{" "}
                  {formatDate(m.created_at, "MMM d, h:mm a")}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      <form
        className="flex items-end gap-2 border-t border-border p-2.5"
        onSubmit={(e) => {
          e.preventDefault();
          send();
        }}
      >
        <textarea
          rows={2}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              send();
            }
          }}
          placeholder="Message Placer…"
          className="w-full flex-1 resize-none rounded-md border border-border-strong bg-bg px-2.5 py-1.5 text-[12.5px] text-text outline-none transition-colors placeholder:text-text-tertiary focus:border-accent focus:ring-2 focus:ring-accent-soft"
        />
        <button
          type="submit"
          disabled={!text.trim() || mutation.isPending}
          className="flex h-7 w-7 shrink-0 cursor-pointer items-center justify-center rounded-md bg-accent text-white transition-colors hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-50"
          aria-label="Send message"
        >
          <SendHorizontal size={14} />
        </button>
      </form>
    </Card>
  );
}
