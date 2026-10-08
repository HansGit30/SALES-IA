function scaled(rawValue: string | number, precision: number): bigint {
  const value = String(rawValue);
  if (!/^\d+(\.\d+)?$/.test(value)) throw new Error("Importe o cantidad inválida");
  const [whole, fraction = ""] = value.split(".");
  if (fraction.length > precision) throw new Error("Demasiados decimales");
  return BigInt(whole) * 10n ** BigInt(precision) + BigInt(fraction.padEnd(precision, "0"));
}

export function lineCents(price: string | number, quantity: string): bigint {
  return (scaled(price, 2) * scaled(quantity, 3) + 500n) / 1000n;
}

export function decimalAmount(cents: bigint): string {
  return `${cents / 100n}.${(cents % 100n).toString().padStart(2, "0")}`;
}

export function saleLineAmounts(price:string|number,quantity:string,discountPercent="0",taxPercent="0") {
  const subtotal=lineCents(price,quantity);
  const discountRate=scaled(discountPercent,2), taxRate=scaled(taxPercent,2);
  if(discountRate>10000n||taxRate>10000n)throw new Error("Los porcentajes deben estar entre 0 y 100");
  const discount=(subtotal*discountRate+5000n)/10000n;
  const taxable=subtotal-discount;
  const tax=(taxable*taxRate+5000n)/10000n;
  return {subtotal,discount,tax,total:taxable+tax};
}
