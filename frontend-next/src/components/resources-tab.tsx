'use client';

import { useState, useMemo } from 'react';
import { Search, Plus, Upload, Filter, Clock, CheckCircle, XCircle, Wrench } from 'lucide-react';
import { toast } from 'sonner';

import api from '@/lib/api';
import type { Resource } from '@/types';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { CreateResourceDialog } from '@/components/create-resource-dialog';
import { UploadCsvDialog } from '@/components/upload-csv-dialog';
import { ReservationDialog } from '@/components/reservation-dialog';
import { AvailabilityDialog } from '@/components/availability-dialog';

interface ResourcesTabProps {
    resources: Resource[];
    onRefresh: () => void;
}

type FilterType = 'all' | 'available' | 'in_use' | 'unavailable';

export function ResourcesTab({ resources, onRefresh }: ResourcesTabProps) {
    const [searchQuery, setSearchQuery] = useState('');
    const [currentFilter, setCurrentFilter] = useState<FilterType>('all');
    const [currentPage, setCurrentPage] = useState(1);
    const [createDialogOpen, setCreateDialogOpen] = useState(false);
    const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
    const [reservationDialogOpen, setReservationDialogOpen] = useState(false);
    const [availabilityDialogOpen, setAvailabilityDialogOpen] = useState(false);
    const [selectedResource, setSelectedResource] = useState<Resource | null>(null);

    const itemsPerPage = 10;

    const filteredResources = useMemo(() => {
        let filtered = resources;

        // Apply search filter
        if (searchQuery) {
            const query = searchQuery.toLowerCase();
            filtered = filtered.filter(
                r =>
                    r.name.toLowerCase().includes(query) ||
                    r.tags.some(t => t.toLowerCase().includes(query))
            );
        }

        // Apply status filter
        if (currentFilter !== 'all') {
            filtered = filtered.filter(r => {
                if (currentFilter === 'available') return r.available;
                if (currentFilter === 'in_use') return r.available && r.status === 'in_use';
                if (currentFilter === 'unavailable') return !r.available;
                return true;
            });
        }

        return filtered;
    }, [resources, searchQuery, currentFilter]);

    const totalPages = Math.ceil(filteredResources.length / itemsPerPage);
    const paginatedResources = filteredResources.slice(
        (currentPage - 1) * itemsPerPage,
        currentPage * itemsPerPage
    );

    const handleReserve = (resource: Resource) => {
        setSelectedResource(resource);
        setReservationDialogOpen(true);
    };

    const handleViewSchedule = (resource: Resource) => {
        setSelectedResource(resource);
        setAvailabilityDialogOpen(true);
    };

    const handleToggleStatus = async (resource: Resource) => {
        try {
            await api.put(`/resources/${resource.id}/availability`, {
                available: !resource.available,
            });
            toast.success(`Resource ${resource.available ? 'disabled' : 'enabled'} successfully`);
            onRefresh();
        } catch {
            toast.error('Failed to update resource status');
        }
    };

    const getStatusIcon = (resource: Resource) => {
        if (!resource.available) return <Wrench className="h-3 w-3" />;
        if (resource.status === 'in_use') return <Clock className="h-3 w-3" />;
        return <CheckCircle className="h-3 w-3" />;
    };

    const getStatusText = (resource: Resource) => {
        if (!resource.available) return 'Maintenance';
        if (resource.status === 'in_use') return 'In Use';
        return 'Available';
    };

    const getStatusVariant = (resource: Resource): 'default' | 'secondary' | 'destructive' | 'outline' => {
        if (!resource.available) return 'destructive';
        if (resource.status === 'in_use') return 'secondary';
        return 'default';
    };

    return (
        <>
            <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
                    <CardTitle>Resources</CardTitle>
                    <div className="flex gap-2">
                        <Button size="sm" variant="outline" onClick={() => setUploadDialogOpen(true)}>
                            <Upload className="mr-2 h-4 w-4" />
                            Upload CSV
                        </Button>
                        <Button size="sm" onClick={() => setCreateDialogOpen(true)}>
                            <Plus className="mr-2 h-4 w-4" />
                            Add Resource
                        </Button>
                    </div>
                </CardHeader>
                <CardContent>
                    {/* Search */}
                    <div className="mb-4 flex gap-2">
                        <div className="relative flex-1">
                            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                            <Input
                                placeholder="Search resources..."
                                value={searchQuery}
                                onChange={e => {
                                    setSearchQuery(e.target.value);
                                    setCurrentPage(1);
                                }}
                                className="pl-9"
                            />
                        </div>
                    </div>

                    {/* Filters */}
                    <div className="mb-4 flex flex-wrap gap-2">
                        {(['all', 'available', 'in_use', 'unavailable'] as FilterType[]).map(filter => (
                            <Button
                                key={filter}
                                variant={currentFilter === filter ? 'default' : 'outline'}
                                size="sm"
                                onClick={() => {
                                    setCurrentFilter(filter);
                                    setCurrentPage(1);
                                }}
                                className="gap-1"
                            >
                                {filter === 'all' && <Filter className="h-3 w-3" />}
                                {filter === 'available' && <CheckCircle className="h-3 w-3" />}
                                {filter === 'in_use' && <Clock className="h-3 w-3" />}
                                {filter === 'unavailable' && <XCircle className="h-3 w-3" />}
                                {filter === 'all' ? 'All Resources' : filter.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                            </Button>
                        ))}
                    </div>

                    {/* Resource List */}
                    <div className="space-y-2">
                        {paginatedResources.length === 0 ? (
                            <div className="flex flex-col items-center justify-center py-12 text-center">
                                <Search className="mb-4 h-12 w-12 text-muted-foreground/50" />
                                <h3 className="text-lg font-semibold">No Resources Found</h3>
                                <p className="text-muted-foreground">
                                    No resources match your current search criteria.
                                </p>
                                <Button
                                    variant="outline"
                                    className="mt-4"
                                    onClick={() => {
                                        setSearchQuery('');
                                        setCurrentFilter('all');
                                    }}
                                >
                                    Clear Filters
                                </Button>
                            </div>
                        ) : (
                            paginatedResources.map(resource => (
                                <div
                                    key={resource.id}
                                    className="flex items-center gap-4 rounded-lg border p-4 transition-colors hover:bg-muted/50"
                                >
                                    {/* Avatar */}
                                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary/10 font-semibold text-primary">
                                        {resource.name.charAt(0).toUpperCase()}
                                    </div>

                                    {/* Content */}
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2">
                                            <h3 className="font-medium truncate">{resource.name}</h3>
                                            <span className="text-xs text-muted-foreground">#{resource.id}</span>
                                        </div>
                                        <div className="flex flex-wrap items-center gap-2 mt-1">
                                            <Badge
                                                variant={getStatusVariant(resource)}
                                                className="cursor-pointer gap-1"
                                                onClick={() => handleToggleStatus(resource)}
                                            >
                                                {getStatusIcon(resource)}
                                                {getStatusText(resource)}
                                            </Badge>
                                            {resource.tags.slice(0, 3).map(tag => (
                                                <Badge key={tag} variant="outline" className="text-xs">
                                                    {tag}
                                                </Badge>
                                            ))}
                                            {resource.tags.length > 3 && (
                                                <span className="text-xs text-muted-foreground">
                                                    +{resource.tags.length - 3} more
                                                </span>
                                            )}
                                        </div>
                                    </div>

                                    {/* Actions */}
                                    <div className="flex shrink-0 gap-2">
                                        <Button
                                            variant="outline"
                                            size="sm"
                                            onClick={() => handleViewSchedule(resource)}
                                        >
                                            Schedule
                                        </Button>
                                        {resource.available && resource.status !== 'in_use' && (
                                            <Button size="sm" onClick={() => handleReserve(resource)}>
                                                Reserve
                                            </Button>
                                        )}
                                    </div>
                                </div>
                            ))
                        )}
                    </div>

                    {/* Pagination */}
                    {totalPages > 1 && (
                        <div className="mt-4 flex items-center justify-between">
                            <span className="text-sm text-muted-foreground">
                                Showing {(currentPage - 1) * itemsPerPage + 1}-
                                {Math.min(currentPage * itemsPerPage, filteredResources.length)} of{' '}
                                {filteredResources.length} resources
                            </span>
                            <div className="flex gap-1">
                                <Button
                                    variant="outline"
                                    size="sm"
                                    disabled={currentPage === 1}
                                    onClick={() => setCurrentPage(p => p - 1)}
                                >
                                    Previous
                                </Button>
                                <Button
                                    variant="outline"
                                    size="sm"
                                    disabled={currentPage === totalPages}
                                    onClick={() => setCurrentPage(p => p + 1)}
                                >
                                    Next
                                </Button>
                            </div>
                        </div>
                    )}
                </CardContent>
            </Card>

            {/* Dialogs */}
            <CreateResourceDialog
                open={createDialogOpen}
                onOpenChange={setCreateDialogOpen}
                onSuccess={onRefresh}
            />
            <UploadCsvDialog
                open={uploadDialogOpen}
                onOpenChange={setUploadDialogOpen}
                onSuccess={onRefresh}
            />
            <ReservationDialog
                open={reservationDialogOpen}
                onOpenChange={setReservationDialogOpen}
                resource={selectedResource}
                onSuccess={onRefresh}
            />
            <AvailabilityDialog
                open={availabilityDialogOpen}
                onOpenChange={setAvailabilityDialogOpen}
                resource={selectedResource}
            />
        </>
    );
}
