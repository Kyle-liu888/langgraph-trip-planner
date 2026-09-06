const provinces = new Set('河北 山西 辽宁 吉林 黑龙江 江苏 浙江 安徽 福建 江西 山东 河南 湖北 湖南 广东 海南 四川 贵州 云南 陕西 甘肃 青海 台湾 内蒙古 广西 西藏 宁夏 新疆'.split(' '))

export function cityInputError(value: string): string | undefined {
  const city = value.trim()
  if (!city) return '请输入目的地城市'
  const region = city.replace(/(壮族自治区|回族自治区|维吾尔自治区|自治区|省)$/, '')
  if (provinces.has(region)) return '请填写具体城市（如昆明、丽江），当前不支持整省或自治区行程'
}

export async function validateCity(_rule: unknown, value: string) {
  const error = cityInputError(value || '')
  if (error) throw new Error(error)
}
