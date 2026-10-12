import { describe, expect, it } from 'vitest';
import { createBlankSchema } from './defaults';
import { cloneWithNewIds, createNode, findNode, findParent, insertNode, moveNode, removeNode, updateNode } from './tree';

function sample() {
  const root = createNode('Column');
  const card = createNode('Card');
  const a = createNode('Text', { props: { text: 'A' } });
  const b = createNode('Text', { props: { text: 'B' } });
  const tree = insertNode(insertNode(insertNode(root, root.id, card), card.id, a), root.id, b);
  return { tree, root, card, a, b };
}

describe('tree helpers', () => {
  it('inserts only into containers', () => {
    const { tree, a } = sample();
    const after = insertNode(tree, a.id, createNode('Text'));
    expect(after).toEqual(tree);
  });

  it('finds nodes and parents', () => {
    const { tree, card, a } = sample();
    expect(findNode(tree, a.id)?.props.text).toBe('A');
    expect(findParent(tree, a.id)).toMatchObject({ parent: { id: card.id }, index: 0 });
  });

  it('updates immutably and keeps untouched branches', () => {
    const { tree, a, b } = sample();
    const after = updateNode(tree, a.id, n => ({ ...n, props: { text: 'A2' } }));
    expect(findNode(after, a.id)?.props.text).toBe('A2');
    expect(findNode(tree, a.id)?.props.text).toBe('A');
    expect(after.children[1]).toBe(tree.children[1]);
    expect(findNode(after, b.id)).toBe(findNode(tree, b.id));
  });

  it('removes nested nodes', () => {
    const { tree, a } = sample();
    expect(findNode(removeNode(tree, a.id), a.id)).toBeNull();
  });

  it('moves between parents and within a parent', () => {
    const { tree, root, card, b } = sample();
    const moved = moveNode(tree, b.id, card.id, 0);
    expect(moved.children.map(c => c.id)).toEqual([card.id]);
    expect(findParent(moved, b.id)).toMatchObject({ parent: { id: card.id }, index: 0 });

    const reordered = moveNode(tree, card.id, root.id, 2);
    expect(reordered.children.map(c => c.id)).toEqual([b.id, card.id]);
  });

  it('refuses to move a node into its own subtree', () => {
    const { tree, card, a } = sample();
    expect(moveNode(tree, card.id, a.id, 0)).toBe(tree);
  });

  it('clones with fresh ids', () => {
    const { card, tree } = sample();
    const original = findNode(tree, card.id)!;
    const copy = cloneWithNewIds(original);
    expect(copy.id).not.toBe(original.id);
    expect(copy.children[0].id).not.toBe(original.children[0].id);
    expect(copy.children[0].props).toEqual(original.children[0].props);
  });

  it('creates a usable blank schema', () => {
    const schema = createBlankSchema('Pet Pal');
    expect(schema.screens).toHaveLength(1);
    expect(schema.navigation.initialScreenId).toBe(schema.screens[0].id);
    expect(schema.build.bundleId).toBe('com.wolf.petpal');
  });
});
