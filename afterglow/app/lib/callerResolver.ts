import type { CallListItem } from './types';
import { findMockContact } from './mockContacts';

export type ResolvedCaller = {
  display_name: string;
  label: string;
  is_customer: boolean;
};

export function resolveFromCallItem(call: CallListItem): ResolvedCaller {
  if (call.customer_display_name) {
    return { display_name: call.customer_display_name, label: 'Client', is_customer: true };
  }
  const mock = findMockContact(call.phone_e164);
  if (mock) {
    return { display_name: mock.display_name, label: mock.label, is_customer: false };
  }
  return { display_name: call.phone_e164, label: 'Unknown', is_customer: false };
}

export function resolveFromPhone(
  phone: string,
  customerNamesByPhone: Map<string, string>,
): ResolvedCaller {
  const name = customerNamesByPhone.get(phone);
  if (name) {
    return { display_name: name, label: 'Client', is_customer: true };
  }
  const mock = findMockContact(phone);
  if (mock) {
    return { display_name: mock.display_name, label: mock.label, is_customer: false };
  }
  return { display_name: phone, label: 'Unknown', is_customer: false };
}
