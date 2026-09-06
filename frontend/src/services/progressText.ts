import { nodeLabels, type ProgressEvent } from './trips'

const names: Record<string, string> = {
  'run.queued': '等待规划', 'run.started': '开始规划', 'run.failed': '规划失败',
  'run.completed': '规划结束', 'run.interrupted': '规划中断',
  'node.started': '开始', 'node.completed': '完成', 'node.failed': '节点失败',
  'model.started': '正在调用模型', 'model.completed': '模型返回',
  'model.failed': '模型请求失败', 'model.waiting': '等待模型',
  'model.progress': '接收模型响应', 'model.cancelled': '模型调用已中断',
  'model.strategy_retry': '切换输出策略', 'prompt.compacted': '规划资料已精简',
  'validation.failed': '候选校验未通过', 'retry.scheduled': '准备再次生成'
}

export function eventText(event: ProgressEvent) {
  return [names[event.type] || event.type, event.label || nodeLabels[event.node || ''] || '',
    event.model || '', event.error_type || ''].filter(Boolean).join(' · ')
}
