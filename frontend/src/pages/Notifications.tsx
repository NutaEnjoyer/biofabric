import { useState } from 'react';
import { Send } from 'lucide-react';
import { Card, CardHeader, CardContent, Button, Input, Select } from '../components/ui';
import { useSendNotification } from '../hooks/useContracts';

const templateOptions = [
  { value: 'contract_expiring', label: 'Истечение договора' },
  { value: 'contract_overdue', label: 'Просрочка договора' },
  { value: 'guarantee_expiring', label: 'Истечение гарантии' },
  { value: 'risk_detected', label: 'Обнаружен риск' },
  { value: 'approval_required', label: 'Требуется согласование' },
];

export function Notifications() {
  const [templateCode, setTemplateCode] = useState('contract_expiring');
  const [recipients, setRecipients] = useState('');
  const [contractNo, setContractNo] = useState('');
  const [message, setMessage] = useState('');
  const [result, setResult] = useState<number | null>(null);

  const sendNotification = useSendNotification();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const to = recipients.split(',').map((r) => r.trim()).filter(Boolean);
    const payload: Record<string, unknown> = {};
    if (contractNo) payload.contract_no = contractNo;
    if (message) payload.message = message;

    const res = await sendNotification.mutateAsync({
      template_code: templateCode,
      to,
      payload,
    });
    setResult(res.outbox_id);
    setRecipients('');
    setContractNo('');
    setMessage('');
  };

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-[#1E293B]">Уведомления</h1>
        <p className="text-[#64748B] mt-1">Отправка уведомлений по шаблонам</p>
      </div>

      <div className="max-w-xl">
        <Card>
          <CardHeader
            title="Отправить уведомление"
            description="Выберите шаблон и укажите получателей"
          />
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <Select
                label="Шаблон"
                options={templateOptions}
                value={templateCode}
                onChange={(e) => setTemplateCode(e.target.value)}
              />
              <Input
                label="Получатели"
                value={recipients}
                onChange={(e) => setRecipients(e.target.value)}
                placeholder="email1@example.com, email2@example.com"
                required
              />
              <Input
                label="№ договора (опционально)"
                value={contractNo}
                onChange={(e) => setContractNo(e.target.value)}
                placeholder="2024-001"
              />
              <div>
                <label className="block text-sm font-medium text-[#1E293B] mb-1.5">
                  Сообщение (опционально)
                </label>
                <textarea
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  placeholder="Дополнительная информация..."
                  className="w-full h-24 px-3 py-2 rounded-lg border border-[#E2E8F0] text-sm resize-none focus:outline-none focus:ring-2 focus:ring-[#2563EB]"
                />
              </div>
              <Button type="submit" loading={sendNotification.isPending}>
                <Send className="w-4 h-4" />
                Отправить
              </Button>
            </form>

            {result && (
              <div className="mt-4 p-4 bg-[#ECFDF5] rounded-lg text-sm">
                <p className="text-[#10B981] font-medium">Уведомление добавлено в очередь</p>
                <p className="text-[#64748B] mt-1">Outbox ID: {result}</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
