import { COMPONENTS, isContainer } from './catalog';
import type { AppSchema, ComponentType, Node, Screen } from './types';

/** Immutable helpers for editing component trees. All return new objects. */

export function newId(): string {
  return globalThis.crypto.randomUUID();
}

export function createNode(type: ComponentType, overrides: Partial<Node> = {}): Node {
  const def = COMPONENTS[type];
  return {
    id: newId(),
    type,
    props: { ...def.defaultProps },
    style: { ...def.defaultStyle },
    children: [],
    ...overrides,
  };
}

export function findNode(root: Node, id: string): Node | null {
  if (root.id === id) return root;
  for (const child of root.children) {
    const found = findNode(child, id);
    if (found) return found;
  }
  return null;
}

/** Returns the parent of `id` and its index, or null for the root / missing nodes. */
export function findParent(root: Node, id: string): { parent: Node; index: number } | null {
  const index = root.children.findIndex(c => c.id === id);
  if (index >= 0) return { parent: root, index };
  for (const child of root.children) {
    const found = findParent(child, id);
    if (found) return found;
  }
  return null;
}

export function updateNode(root: Node, id: string, fn: (node: Node) => Node): Node {
  if (root.id === id) return fn(root);
  let changed = false;
  const children = root.children.map(c => {
    const next = updateNode(c, id, fn);
    if (next !== c) changed = true;
    return next;
  });
  return changed ? { ...root, children } : root;
}

export function removeNode(root: Node, id: string): Node {
  if (!root.children.some(c => c.id === id)) {
    let changed = false;
    const children = root.children.map(c => {
      const next = removeNode(c, id);
      if (next !== c) changed = true;
      return next;
    });
    return changed ? { ...root, children } : root;
  }
  return { ...root, children: root.children.filter(c => c.id !== id) };
}

export function insertNode(root: Node, parentId: string, node: Node, index?: number): Node {
  return updateNode(root, parentId, parent => {
    if (!isContainer(parent.type)) return parent;
    const children = [...parent.children];
    children.splice(index ?? children.length, 0, node);
    return { ...parent, children };
  });
}

/** Moves `id` to `parentId` at `index`. No-op if that would put a node inside itself. */
export function moveNode(root: Node, id: string, parentId: string, index: number): Node {
  const node = findNode(root, id);
  if (!node || id === root.id || findNode(node, parentId)) return root;
  const source = findParent(root, id);
  // Moving within the same parent: account for the gap left by removal.
  const adjusted = source && source.parent.id === parentId && source.index < index ? index - 1 : index;
  return insertNode(removeNode(root, id), parentId, node, adjusted);
}

/** Deep copy with fresh ids, for duplicate / paste. */
export function cloneWithNewIds(node: Node): Node {
  return { ...structuredClone(node), id: newId(), children: node.children.map(cloneWithNewIds) };
}

export function updateScreen(schema: AppSchema, screenId: string, fn: (s: Screen) => Screen): AppSchema {
  return { ...schema, screens: schema.screens.map(s => (s.id === screenId ? fn(s) : s)) };
}

/** Visits every node of every screen. */
export function walk(node: Node, visit: (node: Node, parent: Node | null) => void, parent: Node | null = null): void {
  visit(node, parent);
  for (const child of node.children) walk(child, visit, node);
}
