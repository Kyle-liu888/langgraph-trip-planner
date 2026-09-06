import { describe, expect, it } from 'vitest'
import { cityInputError, validateCity } from './destination'

describe('single-city destination input', () => {
  it.each(['云南', ' 云南省 ', '广西壮族自治区', '内蒙古自治区'])('rejects province-only input %s', async value => {
    expect(cityInputError(value)).toContain('具体城市')
    await expect(validateCity({}, value)).rejects.toThrow('具体城市')
  })
  it.each(['昆明', '丽江市', '北京', '重庆', '大理白族自治州'])('accepts a city or prefecture %s', async value => {
    expect(cityInputError(value)).toBeUndefined()
    await expect(validateCity({}, value)).resolves.toBeUndefined()
  })
})
