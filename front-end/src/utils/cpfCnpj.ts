/** Remove caracteres não numéricos. */
export function digitsOnly(s: string): string {
  return s.replace(/\D/g, "");
}

/** CPF com 11 dígitos e dígitos verificadores válidos. */
export function isValidCPF(raw: string): boolean {
  const cpf = digitsOnly(raw);
  if (cpf.length !== 11) return false;
  if (/^(\d)\1{10}$/.test(cpf)) return false;

  let sum = 0;
  for (let i = 0; i < 9; i++) sum += parseInt(cpf[i]!, 10) * (10 - i);
  let rest = sum % 11;
  const d1 = rest < 2 ? 0 : 11 - rest;
  if (d1 !== parseInt(cpf[9]!, 10)) return false;

  sum = 0;
  for (let i = 0; i < 10; i++) sum += parseInt(cpf[i]!, 10) * (11 - i);
  rest = sum % 11;
  const d2 = rest < 2 ? 0 : 11 - rest;
  return d2 === parseInt(cpf[10]!, 10);
}

/** CNPJ com 14 dígitos e dígitos verificadores válidos. */
export function isValidCNPJ(raw: string): boolean {
  const cnpj = digitsOnly(raw);
  if (cnpj.length !== 14) return false;
  if (/^(\d)\1{13}$/.test(cnpj)) return false;

  const w1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];
  const w2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];

  let sum = 0;
  for (let i = 0; i < 12; i++) sum += parseInt(cnpj[i]!, 10) * w1[i]!;
  let d1 = sum % 11;
  d1 = d1 < 2 ? 0 : 11 - d1;
  if (d1 !== parseInt(cnpj[12]!, 10)) return false;

  sum = 0;
  for (let i = 0; i < 13; i++) sum += parseInt(cnpj[i]!, 10) * w2[i]!;
  let d2 = sum % 11;
  d2 = d2 < 2 ? 0 : 11 - d2;
  return d2 === parseInt(cnpj[13]!, 10);
}

export function isValidCpfOrCnpj(value: string): boolean {
  const d = digitsOnly(value);
  if (d.length === 11) return isValidCPF(d);
  if (d.length === 14) return isValidCNPJ(d);
  return false;
}
