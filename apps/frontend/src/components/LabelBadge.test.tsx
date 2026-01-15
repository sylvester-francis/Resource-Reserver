/**
 * Label component tests.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { LabelBadge, LabelBadgeList, type LabelData } from '@/components/LabelBadge';

// Mock label data
const mockLabel: LabelData = {
    id: 1,
    category: 'environment',
    value: 'production',
    color: '#ef4444',
    description: 'Production environment',
    full_name: 'environment:production',
    resource_count: 5,
};

const mockLabels: LabelData[] = [
    mockLabel,
    {
        id: 2,
        category: 'team',
        value: 'backend',
        color: '#3b82f6',
        description: 'Backend team',
        full_name: 'team:backend',
        resource_count: 3,
    },
    {
        id: 3,
        category: 'type',
        value: 'server',
        color: '#22c55e',
        description: null,
        full_name: 'type:server',
    },
    {
        id: 4,
        category: 'region',
        value: 'us-east',
        color: '#8b5cf6',
        description: 'US East region',
        full_name: 'region:us-east',
    },
];

describe('LabelBadge', () => {
    it('renders with correct text', () => {
        render(<LabelBadge label={mockLabel} />);
        expect(screen.getByText('environment:')).toBeInTheDocument();
        expect(screen.getByText('production')).toBeInTheDocument();
    });

    it('renders without category when showCategory is false', () => {
        render(<LabelBadge label={mockLabel} showCategory={false} />);
        expect(screen.queryByText('environment:')).not.toBeInTheDocument();
        expect(screen.getByText('production')).toBeInTheDocument();
    });

    it('applies correct background color', () => {
        const { container } = render(<LabelBadge label={mockLabel} />);
        const badge = container.firstChild as HTMLElement;
        expect(badge).toHaveStyle({ backgroundColor: '#ef4444' });
    });

    it('shows tooltip text with description', () => {
        const { container } = render(<LabelBadge label={mockLabel} />);
        const badge = container.firstChild as HTMLElement;
        expect(badge).toHaveAttribute('title', 'Production environment');
    });

    it('handles missing description gracefully', () => {
        const labelWithoutDesc = { ...mockLabel, description: null };
        const { container } = render(<LabelBadge label={labelWithoutDesc} />);
        const badge = container.firstChild as HTMLElement;
        expect(badge).not.toHaveAttribute('title');
    });

    it('calls onClick when clicked', () => {
        const onClick = vi.fn();
        render(<LabelBadge label={mockLabel} onClick={onClick} />);
        fireEvent.click(screen.getByText('production'));
        expect(onClick).toHaveBeenCalled();
    });

    it('shows remove button when onRemove is provided', () => {
        const onRemove = vi.fn();
        render(<LabelBadge label={mockLabel} onRemove={onRemove} />);
        const removeButton = screen.getByRole('button', { name: /remove/i });
        expect(removeButton).toBeInTheDocument();
        fireEvent.click(removeButton);
        expect(onRemove).toHaveBeenCalled();
    });

    it('applies different size classes', () => {
        const { rerender, container } = render(<LabelBadge label={mockLabel} size="sm" />);
        expect(container.firstChild).toHaveClass('text-xs');
        expect(container.firstChild).toHaveClass('px-1.5');

        rerender(<LabelBadge label={mockLabel} size="lg" />);
        expect(container.firstChild).toHaveClass('text-sm');
        expect(container.firstChild).toHaveClass('px-2.5');
    });
});

describe('LabelBadgeList', () => {
    it('renders all labels when count is within limit', () => {
        const twoLabels = mockLabels.slice(0, 2);
        render(<LabelBadgeList labels={twoLabels} maxDisplay={3} />);
        expect(screen.getByText('production')).toBeInTheDocument();
        expect(screen.getByText('backend')).toBeInTheDocument();
    });

    it('shows overflow indicator when labels exceed maxDisplay', () => {
        render(<LabelBadgeList labels={mockLabels} maxDisplay={2} />);
        expect(screen.getByText('+2 more')).toBeInTheDocument();
    });

    it('calls onRemove for individual labels', () => {
        const onRemove = vi.fn();
        render(<LabelBadgeList labels={mockLabels.slice(0, 2)} onRemove={onRemove} />);

        const removeButtons = screen.getAllByRole('button', { name: /remove/i });
        fireEvent.click(removeButtons[0]);

        expect(onRemove).toHaveBeenCalledWith(mockLabels[0]);
    });

    it('shows dropdown menu for hidden labels on overflow indicator', () => {
        render(<LabelBadgeList labels={mockLabels} maxDisplay={2} />);
        const overflow = screen.getByText('+2 more');
        // Overflow indicator is now a dropdown trigger button
        expect(overflow).toBeInTheDocument();
        expect(overflow.closest('button')).toBeInTheDocument();
    });
});
