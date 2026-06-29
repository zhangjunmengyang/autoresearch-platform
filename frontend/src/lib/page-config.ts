import {
  Brain,
  FlaskConical,
  LayoutDashboard,
  Lightbulb,
  ListChecks,
  ScrollText,
  Server,
  Sparkles,
} from 'lucide-react'

export const navGroups = [
  {
    title: '方法论',
    items: [
      { path: '/dashboard', label: '总览看板', icon: LayoutDashboard },
      { path: '/sources', label: 'Idea Pool 想法池', icon: ScrollText },
      { path: '/insights', label: 'Hypothesis 假设', icon: Lightbulb },
    ],
  },
  {
    title: '研究',
    items: [
      {
        path: '/research',
        label: 'Plan / Experiment 计划实验',
        icon: ListChecks,
        activePaths: ['/research/methodology', '/research-queue', '/research/context', '/research/readiness', '/research/rounds', '/research/audit'],
      },
      { path: '/sessions', label: 'Experiment 账本', icon: FlaskConical },
      {
        path: '/evidence',
        label: 'Review / Decision 复盘决策',
        icon: Sparkles,
        activePaths: ['/artifacts', '/benchmarks', '/reviews', '/decisions'],
      },
    ],
  },
  {
    title: '知识',
    items: [
      { path: '/knowledge/experiences', label: 'Lesson 经验', icon: Brain },
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
