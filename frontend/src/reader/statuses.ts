export const STATUS_BUTTONS: { status: number; label: string; title: string }[] = [
  { status: 1, label: '1', title: 'New' },
  { status: 2, label: '2', title: 'Recognised' },
  { status: 3, label: '3', title: 'Familiar' },
  { status: 4, label: '4', title: 'Learned' },
  { status: 5, label: '5', title: 'Known' },
  { status: 99, label: '✓', title: 'Well known' },
  { status: 98, label: '✕', title: 'Ignore' },
]

export const statusName = (status: number) =>
  status === 99 ? 'well known' : status === 98 ? 'ignored' : `status ${status}`
