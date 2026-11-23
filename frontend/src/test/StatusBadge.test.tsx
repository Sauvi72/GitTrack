import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import React from 'react';
import { StatusBadge } from '../components/StatusBadge';

describe('StatusBadge component', () => {
  it('renders MERGED status correctly', () => {
    render(<StatusBadge status="MERGED" />);
    expect(screen.getByText('Merged')).toBeInTheDocument();
  });

  it('renders OPEN status correctly', () => {
    render(<StatusBadge status="OPEN" />);
    expect(screen.getByText('Open')).toBeInTheDocument();
  });

  it('renders CLOSED_UNMERGED status correctly', () => {
    render(<StatusBadge status="CLOSED_UNMERGED" />);
    expect(screen.getByText('Closed Unmerged')).toBeInTheDocument();
  });
});
