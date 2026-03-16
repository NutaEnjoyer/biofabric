import { useState } from 'react';
import { Upload, Send } from 'lucide-react';
import { Card, CardHeader, CardContent, Button, Input } from '../components/ui';
import { useEnqueueEIS, useStage1C, useUpsert1C } from '../hooks/useContracts';

export function Integrations() {
  // EIS state
  const [eisContractId, setEisContractId] = useState('');
  const [eisResult, setEisResult] = useState<{ queue_id: number; job_id: string } | null>(null);
  const enqueueEIS = useEnqueueEIS();

  // 1C state
  const [jsonInput, setJsonInput] = useState('');
  const [stageId, setStageId] = useState<number | null>(null);
  const [importResult, setImportResult] = useState<number | null>(null);
  const stage1C = useStage1C();
  const upsert1C = useUpsert1C();

  const handleEISSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const result = await enqueueEIS.mutateAsync({
      contract_id: Number(eisContractId),
      payload: { source: 'frontend' },
    });
    setEisResult(result);
    setEisContractId('');
  };

  const handleStage = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const payload = JSON.parse(jsonInput);
      const result = await stage1C.mutateAsync({ payload });
      setStageId(result.stage_id);
    } catch {
      alert('Невалидный JSON');
    }
  };

  const handleUpsert = async () => {
    if (!stageId) return;
    const result = await upsert1C.mutateAsync(stageId);
    setImportResult(result.contract_id);
    setStageId(null);
    setJsonInput('');
  };

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-[#1E293B]">Интеграции</h1>
        <p className="text-[#64748B] mt-1">ЕИС и 1С</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* EIS */}
        <Card>
          <CardHeader
            title="Экспорт в ЕИС"
            description="Поставить договор в очередь отправки"
          />
          <CardContent>
            <form onSubmit={handleEISSubmit} className="space-y-4">
              <Input
                label="ID договора"
                type="number"
                value={eisContractId}
                onChange={(e) => setEisContractId(e.target.value)}
                placeholder="123"
                required
              />
              <Button type="submit" loading={enqueueEIS.isPending}>
                <Send className="w-4 h-4" />
                Отправить в ЕИС
              </Button>
            </form>

            {eisResult && (
              <div className="mt-4 p-4 bg-[#ECFDF5] rounded-lg text-sm">
                <p className="text-[#10B981] font-medium">Успешно добавлено в очередь</p>
                <p className="text-[#64748B] mt-1">Queue ID: {eisResult.queue_id}</p>
                <p className="text-[#64748B]">Job ID: {eisResult.job_id}</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* 1C Import */}
        <Card>
          <CardHeader
            title="Импорт из 1С"
            description="Загрузить данные договора из JSON"
          />
          <CardContent>
            <form onSubmit={handleStage} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-[#1E293B] mb-1.5">
                  JSON данные
                </label>
                <textarea
                  value={jsonInput}
                  onChange={(e) => setJsonInput(e.target.value)}
                  placeholder='{"contract_no": "2024-001", "title": "Договор поставки"}'
                  className="w-full h-32 px-3 py-2 rounded-lg border border-[#E2E8F0] text-sm font-mono resize-none focus:outline-none focus:ring-2 focus:ring-[#2563EB]"
                  required
                />
              </div>
              <div className="flex gap-3">
                <Button type="submit" variant="secondary" loading={stage1C.isPending}>
                  <Upload className="w-4 h-4" />
                  Загрузить в staging
                </Button>
                {stageId && (
                  <Button onClick={handleUpsert} loading={upsert1C.isPending}>
                    Применить (ID: {stageId})
                  </Button>
                )}
              </div>
            </form>

            {importResult && (
              <div className="mt-4 p-4 bg-[#ECFDF5] rounded-lg text-sm">
                <p className="text-[#10B981] font-medium">Договор создан/обновлён</p>
                <p className="text-[#64748B] mt-1">Contract ID: {importResult}</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
