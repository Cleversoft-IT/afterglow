export type PersonalContact = {
  id: string;
  display_name: string;
  phone_e164: string;
  label: 'Mobile' | 'Work' | 'Home' | 'Main';
};

export const MOCK_CONTACTS: PersonalContact[] = [
  { id: 'pc_001', display_name: 'Amelia Brooks',     phone_e164: '+447911100001', label: 'Mobile' },
  { id: 'pc_002', display_name: 'Benjamin Clark',    phone_e164: '+447911100002', label: 'Work' },
  { id: 'pc_003', display_name: 'Charlotte Davies',  phone_e164: '+447911100003', label: 'Home' },
  { id: 'pc_004', display_name: 'Daniel Edwards',    phone_e164: '+447911100004', label: 'Mobile' },
  { id: 'pc_005', display_name: 'Eleanor Foster',    phone_e164: '+447911100005', label: 'Main' },
  { id: 'pc_006', display_name: 'Finn Gallagher',    phone_e164: '+447911100006', label: 'Mobile' },
  { id: 'pc_007', display_name: 'Grace Harrison',    phone_e164: '+447911100007', label: 'Work' },
  { id: 'pc_008', display_name: 'Henry Iverson',     phone_e164: '+447911100008', label: 'Home' },
  { id: 'pc_009', display_name: 'Isla Johnson',      phone_e164: '+447911100009', label: 'Mobile' },
  { id: 'pc_010', display_name: 'Jack Kennedy',      phone_e164: '+447911100010', label: 'Work' },
  { id: 'pc_011', display_name: 'Katherine Lewis',   phone_e164: '+447911100011', label: 'Mobile' },
  { id: 'pc_012', display_name: 'Liam Martinez',     phone_e164: '+447911100012', label: 'Main' },
  { id: 'pc_013', display_name: 'Mia Nguyen',        phone_e164: '+447911100013', label: 'Mobile' },
  { id: 'pc_014', display_name: 'Noah Owens',        phone_e164: '+447911100014', label: 'Work' },
  { id: 'pc_015', display_name: 'Olivia Patel',      phone_e164: '+447911100015', label: 'Home' },
  { id: 'pc_016', display_name: 'Peter Quinn',       phone_e164: '+447911100016', label: 'Mobile' },
  { id: 'pc_017', display_name: 'Rosie Stewart',     phone_e164: '+447911100017', label: 'Work' },
  { id: 'pc_018', display_name: 'Samuel Thompson',   phone_e164: '+447911100018', label: 'Mobile' },
  { id: 'pc_019', display_name: 'Tara Underwood',    phone_e164: '+447911100019', label: 'Main' },
  { id: 'pc_020', display_name: 'Victor Wallace',    phone_e164: '+447911100020', label: 'Mobile' },
];

function normalisePhone(phone: string): string {
  return phone.replace(/\s+/g, '');
}

export function findMockContact(phone: string): PersonalContact | null {
  const target = normalisePhone(phone);
  return MOCK_CONTACTS.find((c) => normalisePhone(c.phone_e164) === target) ?? null;
}
