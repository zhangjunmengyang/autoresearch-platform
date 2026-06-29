import {
  Brain,
  FlaskConical,
  GitBranch,
  History,
  LayoutDashboard,
  Lightbulb,
  ListChecks,
  PackageSearch,
  Radar,
  ScrollText,
  Server,
  Sparkles,
} from 'lucide-react'

export const navGroups = [
  {
    title: '输入',
    items: [
      { path: '/dashboard', label: '总览看板', icon: LayoutDashboard },
      { path: '/sources', label: '资料输入', icon: ScrollText },
      { path: '/insights', label: '洞察与假设', icon: Lightbulb },
    ],
  },
  {
    title: '研究',
    items: [
      { path: '/research/methodology', label: '科研方法论', icon: Lightbulb },
      { path: '/research-queue', label: '研究队列', icon: ListChecks },
      { path: '/research/context', label: '研究上下文', icon: History },
      { path: '/research/readiness', label: '就绪检查', icon: ListChecks },
      { path: '/research/rounds', label: '研究轮次', icon: GitBranch },
      { path: '/sessions', label: '研究账本', icon: FlaskConical },
      { path: '/research/audit', label: '过程审计', icon: History },
      { path: '/evidence', label: '证据记录', icon: ListChecks },
      { path: '/artifacts', label: '成果引用', icon: PackageSearch },
      { path: '/benchmarks', label: '评测登记', icon: Radar },
      { path: '/reviews', label: '审查事件', icon: Sparkles },
      { path: '/decisions', label: '决策记录', icon: ListChecks },
    ],
  },
  {
    title: '知识',
    items: [
      { path: '/knowledge/experiences', label: '长期经验', icon: Brain },
    ],
  },
  {
    title: '系统',
    items: [
      { path: '/capabilities', label: '能力目录', icon: Sparkles },
      { path: '/status', label: '系统状态', icon: Server },
    ],
  },
]
