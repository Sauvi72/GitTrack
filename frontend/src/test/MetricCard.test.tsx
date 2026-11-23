import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import React from 'react';
import { MetricCard } from '../components/MetricCard';

describe('MetricCard component', () => {
  it('renders title and formatted value', () => {
    render(
      <MetricCard
        title="Total PRs"
        value={42}
        subtitle="Across all repos"
        icon={<span>Icon</span>}
      />
    );
    expect(screen.getByText('Total PRs')).toBeInTheDocument();
    expect(screen.getByText('42')).toBeInTheDocument();
    expect(screen.getByText('Across all repos')).toBeInTheDocument();
  });
});
