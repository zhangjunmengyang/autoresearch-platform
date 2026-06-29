import {
  FileText,
  LayoutDashboard,
  ListChecks,
  Server,
  Sparkles,
} from 'lucide-react'

export const navGroups = [
  {
    title: '运行',
    items: [
      { path: '/dashboard', label: '自动研究看板', icon: LayoutDashboard },
      {
        path: '/research',
        label: '研究运行',
        icon: ListChecks,
        activePaths: [
          '/sources',
          '/insights',
          '/research/methodology',
          '/research-queue',
          '/research/context',
          '/research/readiness',
          '/research/rounds',
          '/research/audit',
          '/sessions',
        ],
      },
      {
        path: '/artifacts',
        label: '成果',
        icon: FileText,
        activePaths: ['/artifacts', '/benchmarks', '/reviews', '/decisions'],
      },
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
