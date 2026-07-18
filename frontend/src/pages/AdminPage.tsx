import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { RotateCcw } from "lucide-react";
import { adminApi, API_BASE_URL } from "../lib/api";
import { Button, Card, CardHeader, CenteredSpinner, ErrorState, Kv, PageHeader } from "../components/ui";
import { Checkbox } from "../components/form";
import { errorMessage, useToast } from "../lib/toast";
import { humanize } from "../lib/enums";

export default function AdminPage() {
  const toast = useToast();
  const qc = useQueryClient();
  const [heroesOnly, setHeroesOnly] = useState(false);

  const healthQuery = useQuery({ queryKey: ["admin-health"], queryFn: adminApi.health });
  const statsQuery = useQuery({ queryKey: ["admin-stats"], queryFn: adminApi.stats });

  const resetMutation = useMutation({
    mutationFn: () => adminApi.reset(heroesOnly),
    onSuccess: () => {
      toast.success("Database reset to seed state");
      qc.invalidateQueries();
    },
    onError: (err) => toast.error(errorMessage(err)),
  });

  return (
    <div className="flex h-full flex-col">
      <PageHeader title="Admin" subtitle="Service health, row counts, and the demo reset" />

      <div className="flex-1 overflow-y-auto p-5">
        <div className="grid grid-cols-2 gap-4">
          <Card>
            <CardHeader title="Service" />
            {healthQuery.isLoading && <CenteredSpinner />}
            {healthQuery.isError && <ErrorState message={errorMessage(healthQuery.error)} />}
            {healthQuery.data && (
              <div className="divide-y divide-border px-4">
                <Kv label="Status" value={healthQuery.data.status} />
                <Kv label="Service" value={healthQuery.data.service} />
                <Kv label="Version" value={healthQuery.data.version} />
                <Kv label="API base URL" value={<span className="font-mono text-[11.5px]">{API_BASE_URL}</span>} />
              </div>
            )}
          </Card>

          <Card>
            <CardHeader title="Reset database" subtitle="Drops all data and reseeds from the fixed seed set" />
            <div className="flex flex-col gap-3 px-4 py-3">
              <Checkbox label="Heroes only (skip the 25 imported FHIR patients — faster)" checked={heroesOnly} onChange={(e) => setHeroesOnly(e.target.checked)} />
              <Button variant="danger" size="sm" loading={resetMutation.isPending} onClick={() => resetMutation.mutate()} className="self-start">
                <RotateCcw size={13} /> Reset to seed state
              </Button>
            </div>
          </Card>

          <Card className="col-span-2">
            <CardHeader title="Row counts" />
            {statsQuery.isLoading && <CenteredSpinner />}
            {statsQuery.isError && <ErrorState message={errorMessage(statsQuery.error)} />}
            {statsQuery.data && (
              <div className="grid grid-cols-3 gap-x-6 px-4 divide-y-0">
                {Object.entries(statsQuery.data).map(([table, count]) => (
                  <Kv key={table} label={humanize(table)} value={String(count)} />
                ))}
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
