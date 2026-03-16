import { FileText, Shield, AlertTriangle, Clock } from 'lucide-react';
import { MetricCard } from '../components/ui';
import { useContracts, useGuaranteeShare, useIssues, useMarkOverdue } from '../hooks/useContracts';
import { Button } from '../components/ui';
import { useState } from 'react';

export function Dashboard() {
  const { data: contractsData } = useContracts({ limit: 1000 });
  const { data: guaranteeData } = useGuaranteeShare();
  const { data: issuesData } = useIssues();
  const markOverdue = useMarkOverdue();
  const [markResult, setMarkResult] = useState<number | null>(null);

  const totalContracts = contractsData?.count || 0;
  const guaranteePct = guaranteeData?.pct || 0;
  const totalRisks = issuesData?.reduce((sum, i) => sum + i.risks_cnt, 0) || 0;
  const overdueCount = contractsData?.items.filter(c => c.status_code === 'overdue').length || 0;

  const handleMarkOverdue = async () => {
    const result = await markOverdue.mutateAsync();
    setMarkResult(result.affected);
    setTimeout(() => setMarkResult(null), 3000);
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-[#1E293B]">Дашборд</h1>
          <p className="text-[#64748B] mt-1">Обзор модуля юристов</p>
        </div>
        <Button onClick={handleMarkOverdue} loading={markOverdue.isPending} variant="secondary">
          <Clock className="w-4 h-4" />
          Пометить просроченные
        </Button>
      </div>

      {markResult !== null && (
        <div className="mb-6 p-4 bg-[#ECFDF5] border border-[#10B981] rounded-lg text-[#10B981]">
          Помечено просроченных договоров: {markResult}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard
          title="Всего договоров"
          value={totalContracts}
          icon={FileText}
          iconColor="text-[#2563EB]"
          iconBg="bg-blue-50"
        />
        <MetricCard
          title="С гарантией"
          value={`${guaranteePct}%`}
          subtitle={`${guaranteeData?.with_guarantee || 0} из ${guaranteeData?.total || 0}`}
          icon={Shield}
          iconColor="text-[#10B981]"
          iconBg="bg-[#ECFDF5]"
        />
        <MetricCard
          title="Открытых рисков"
          value={totalRisks}
          icon={AlertTriangle}
          iconColor="text-[#F59E0B]"
          iconBg="bg-[#FFFBEB]"
        />
        <MetricCard
          title="Просрочено"
          value={overdueCount}
          icon={Clock}
          iconColor="text-[#EF4444]"
          iconBg="bg-[#FEF2F2]"
        />
      </div>
    </div>
  );
}
