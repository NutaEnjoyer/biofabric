import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardHeader, CardContent, Table, Select, Badge } from '../components/ui';
import { useIssues, useContractsWithoutGuarantee } from '../hooks/useContracts';
import type { ContractIssueRow, ContractShort } from '../types/contracts';

const severityOptions = [
  { value: '', label: 'Все уровни' },
  { value: '1', label: 'Уровень 1+' },
  { value: '2', label: 'Уровень 2+' },
  { value: '3', label: 'Уровень 3+' },
  { value: '4', label: 'Уровень 4+' },
  { value: '5', label: 'Уровень 5' },
];

export function Issues() {
  const [minSeverity, setMinSeverity] = useState('');
  const navigate = useNavigate();

  const { data: issuesData, isLoading: issuesLoading } = useIssues(
    minSeverity ? Number(minSeverity) : undefined
  );
  const { data: noGuaranteeData, isLoading: noGuaranteeLoading } = useContractsWithoutGuarantee();

  const issuesWithProblems = issuesData?.filter(i => i.risks_cnt > 0 || i.deviations_cnt > 0) || [];

  const issueColumns = [
    {
      key: 'contract_id',
      header: 'ID договора',
      render: (item: ContractIssueRow) => (
        <span className="font-medium">#{item.contract_id}</span>
      ),
    },
    {
      key: 'risks_cnt',
      header: 'Рисков',
      render: (item: ContractIssueRow) => (
        <Badge variant={item.risks_cnt > 0 ? 'danger' : 'default'}>
          {item.risks_cnt}
        </Badge>
      ),
    },
    {
      key: 'deviations_cnt',
      header: 'Отклонений',
      render: (item: ContractIssueRow) => (
        <Badge variant={item.deviations_cnt > 0 ? 'warning' : 'default'}>
          {item.deviations_cnt}
        </Badge>
      ),
    },
  ];

  const noGuaranteeColumns = [
    {
      key: 'contract_no',
      header: '№ договора',
      render: (item: ContractShort) => (
        <span className="font-medium">{item.contract_no}</span>
      ),
    },
    {
      key: 'title',
      header: 'Название',
    },
  ];

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-[#1E293B]">Риски и отклонения</h1>
        <p className="text-[#64748B] mt-1">Мониторинг проблемных договоров</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Issues */}
        <Card>
          <CardHeader
            title="Сводка по рискам"
            description={`Договоров с проблемами: ${issuesWithProblems.length}`}
            action={
              <Select
                options={severityOptions}
                value={minSeverity}
                onChange={(e) => setMinSeverity(e.target.value)}
                className="w-36"
              />
            }
          />
          <CardContent className="p-0">
            <Table
              columns={issueColumns}
              data={issuesWithProblems}
              keyExtractor={(item) => item.contract_id}
              onRowClick={(item) => navigate(`/contracts/${item.contract_id}`)}
              loading={issuesLoading}
              emptyMessage="Проблемных договоров нет"
            />
          </CardContent>
        </Card>

        {/* Without guarantee */}
        <Card>
          <CardHeader
            title="Без банковской гарантии"
            description={`Договоров: ${noGuaranteeData?.length || 0}`}
          />
          <CardContent className="p-0">
            <Table
              columns={noGuaranteeColumns}
              data={noGuaranteeData || []}
              keyExtractor={(item) => item.contract_id}
              onRowClick={(item) => navigate(`/contracts/${item.contract_id}`)}
              loading={noGuaranteeLoading}
              emptyMessage="Все договоры с гарантией"
            />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
