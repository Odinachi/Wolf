import { DEFAULT_THEME, type ComponentType, type Navigation, type Node, type NodeStyle, type Screen, type Theme } from '@wolf/schema';

/** Hand-made example apps shown on the landing page. They are real Wolf schemas. */

let seq = 0;
function n(type: ComponentType, props: Record<string, unknown> = {}, style: NodeStyle = {}, children: Node[] = []): Node {
  return { id: `ex-${++seq}`, type, props, style, children };
}

function screen(name: string, children: Node[], rootStyle: NodeStyle = { padding: 16, gap: 16 }): Screen {
  return { id: `ex-screen-${name}`, name, frame: { x: 0, y: 0 }, root: n('Column', {}, rootStyle, children) };
}

export interface Example {
  name: string;
  prompt: string;
  theme: Theme;
  screen: Screen;
  navigation?: Navigation;
}

const plantTheme: Theme = { ...DEFAULT_THEME, primary: '#2E7D32', secondary: '#558B2F', background: '#F7F8F3', surface: '#FFFFFF', text: '#1A1C18', mutedText: '#5C6157', radius: 16, fontFamily: 'DM Sans' };
const plant = screen('Plants', [
  n('AppBar', { title: 'My jungle', actionIcon: 'notifications_none' }),
  n('Text', { text: 'Good morning, Ada', variant: 'headline' }, { fontWeight: 700 }),
  n('Card', {}, { padding: 16, borderRadius: 20, backgroundColor: '#2E7D32', gap: 6, elevation: 0 }, [
    n('Text', { text: '3 plants need water today', variant: 'title' }, { color: '#FFFFFF', fontWeight: 700 }),
    n('Text', { text: 'Monstera, Fern and Pothos', variant: 'body' }, { color: '#C8E6C9' }),
    n('ProgressBar', { value: 0.4 }),
  ]),
  n('ListView', { direction: 'horizontal' }, { gap: 8, height: 36 }, [
    n('Chip', { label: 'All', selected: true }), n('Chip', { label: 'Indoor' }), n('Chip', { label: 'Succulents' }),
  ]),
  n('Grid', { columns: 2, aspectRatio: 0.82 }, { gap: 12 }, [
    n('Card', {}, { padding: 10, borderRadius: 16, gap: 6, elevation: 0, backgroundColor: '#FFFFFF' }, [
      n('Image', { src: 'https://picsum.photos/seed/monstera/300/300' }, { height: 104, borderRadius: 12 }),
      n('Text', { text: 'Monstera', variant: 'title' }, { fontWeight: 600 }),
      n('Text', { text: 'Water in 1 day', variant: 'caption' }),
    ]),
    n('Card', {}, { padding: 10, borderRadius: 16, gap: 6, elevation: 0, backgroundColor: '#FFFFFF' }, [
      n('Image', { src: 'https://picsum.photos/seed/fernleaf/300/300' }, { height: 104, borderRadius: 12 }),
      n('Text', { text: 'Boston Fern', variant: 'title' }, { fontWeight: 600 }),
      n('Text', { text: 'Water today', variant: 'caption' }),
    ]),
  ]),
]);

const fitTheme: Theme = { ...DEFAULT_THEME, brightness: 'dark', primary: '#FF4F7B', secondary: '#FF8A65', background: '#0E0E12', surface: '#1A1A21', text: '#F4F4F6', mutedText: '#A0A0AB', radius: 14, fontFamily: 'Poppins' };
const fit = screen('Today', [
  n('Row', {}, { gap: 12 }, [
    n('Avatar', { initials: 'JO', size: 44 }, { backgroundColor: '#FF4F7B' }),
    n('Column', {}, { gap: 0, expand: true }, [
      n('Text', { text: 'Tuesday, Oct 14', variant: 'caption' }),
      n('Text', { text: "Let's move, Jo", variant: 'title' }, { fontWeight: 700, fontSize: 18 }),
    ]),
    n('IconButton', { icon: 'local_fire_department' }, { color: '#FF8A65' }),
  ]),
  n('Card', {}, { padding: 18, borderRadius: 22, gap: 10, elevation: 0, backgroundColor: '#1A1A21' }, [
    n('Text', { text: 'Daily goal', variant: 'label' }, { color: '#A0A0AB' }),
    n('Text', { text: '642 / 800 kcal', variant: 'headline' }, { fontWeight: 700 }),
    n('ProgressBar', { value: 0.8 }),
    n('Row', {}, { mainAxisAlignment: 'spaceBetween' }, [
      n('Text', { text: '8,214 steps', variant: 'caption' }), n('Text', { text: '42 min active', variant: 'caption' }),
    ]),
  ]),
  n('Text', { text: 'Up next', variant: 'title' }, { fontWeight: 600 }),
  n('Card', {}, { padding: 0, borderRadius: 20, elevation: 0, backgroundColor: '#1A1A21' }, [
    n('Image', { src: 'https://picsum.photos/seed/hiitworkout/600/320' }, { height: 150 }),
    n('Container', {}, { padding: 14, gap: 4 }, [
      n('Text', { text: 'HIIT Burner · 20 min', variant: 'title' }, { fontWeight: 600 }),
      n('Text', { text: 'Full body · No equipment', variant: 'caption' }),
    ]),
  ]),
  n('Button', { label: 'Start workout', icon: 'play_arrow' }),
]);
const fitNav: Navigation = {
  type: 'tabs', initialScreenId: fit.id,
  tabs: [{ screenId: fit.id, label: 'Today', icon: 'today' }, { screenId: 'x1', label: 'Workouts', icon: 'fitness_center' }, { screenId: 'x2', label: 'Profile', icon: 'person' }],
};

const coffeeTheme: Theme = { ...DEFAULT_THEME, primary: '#8B5E3C', secondary: '#C08552', background: '#FFF8F1', surface: '#FFFFFF', text: '#2B1D14', mutedText: '#7A6658', radius: 14, fontFamily: 'Fraunces' };
const coffee = screen('Order', [
  n('AppBar', { title: 'Bean & Leaf', showBack: false, actionIcon: 'shopping_bag' }),
  n('TextField', { label: 'Search drinks', icon: 'search' }),
  n('Image', { src: 'https://picsum.photos/seed/latteart/700/400' }, { height: 160, borderRadius: 18 }),
  n('Text', { text: 'Popular now', variant: 'title' }, { fontWeight: 700, fontSize: 18 }),
  n('ListTile', { title: 'Oat Flat White', subtitle: '$4.80 · 160 kcal', leadingIcon: 'coffee', trailingIcon: 'add_circle' }),
  n('Divider'),
  n('ListTile', { title: 'Iced Caramel Latte', subtitle: '$5.20 · 210 kcal', leadingIcon: 'local_cafe', trailingIcon: 'add_circle' }),
  n('Divider'),
  n('ListTile', { title: 'Matcha Cloud', subtitle: '$5.50 · 140 kcal', leadingIcon: 'emoji_food_beverage', trailingIcon: 'add_circle' }),
  n('Button', { label: 'Checkout · $15.50' }),
]);

export const EXAMPLES: Example[] = [
  { name: 'Plant Pal', prompt: 'A plant care app with watering reminders', theme: plantTheme, screen: plant },
  { name: 'Pulse', prompt: 'A dark, energetic fitness tracker', theme: fitTheme, screen: fit, navigation: fitNav },
  { name: 'Bean & Leaf', prompt: 'A cozy coffee shop ordering app', theme: coffeeTheme, screen: coffee },
];

export const PROMPT_IDEAS = [
  'A habit tracker with streaks and gentle reminders',
  'A recipe app that plans meals for the week',
  'A marketplace for second-hand sneakers',
  'A budgeting app for couples with shared goals',
  'A dog-walking app with live walk updates',
  'A language-learning app with daily 5-minute lessons',
];
