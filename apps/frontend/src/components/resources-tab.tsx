/**
 * Resources tab component.
 */

'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import {
    Search,
    Plus,
    Upload,
    Filter,
    Clock,
    CheckCircle,
    XCircle,
    Wrench,
    ArrowUpWideNarrow,
    ArrowDownWideNarrow,
    Tag,
    X,
} from 'lucide-react';
import { toast } from 'sonner';

import api from '@/lib/api';
import { usePagination } from '@/hooks/use-pagination';
import type { Resource } from '@/types';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Pagination } from '@/components/pagination';
import { AvailabilityDialog } from '@/components/availability-dialog';
import { BusinessHoursEditor } from '@/components/BusinessHoursEditor';
import { CreateResourceDialog } from '@/components/create-resource-dialog';
import { EditResourceDialog } from '@/components/edit-resource-dialog';
import { ReservationDialog } from '@/components/reservation-dialog';
import { TagManager } from '@/components/tag-manager';
import { UploadCsvDialog } from '@/components/upload-csv-dialog';
import { LabelBadgeList, type LabelData } from '@/components/LabelBadge';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';

interface ResourcesTabProps {
    onRefresh: () => void;
    isAdmin?: boolean;
}

type FilterType = 'all' | 'available' | 'in_use' | 'unavailable';

export function ResourcesTab({ onRefresh, isAdmin = false }: ResourcesTabProps) {
    const [searchQuery, setSearchQuery] = useState('');
    const [currentFilter, setCurrentFilter] = useState<FilterType>('all');
    const [sortBy, setSortBy] = useState('name');
    const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');
    const [createDialogOpen, setCreateDialogOpen] = useState(false);
    const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
    const [reservationDialogOpen, setReservationDialogOpen] = useState(false);
    const [availabilityDialogOpen, setAvailabilityDialogOpen] = useState(false);
    const [selectedResource, setSelectedResource] = useState<Resource | null>(null);
    const [availableTags, setAvailableTags] = useState<string[]>([]);
    const [selectedTags, setSelectedTags] = useState<string[]>([]);

    // Fetch available tags
    const fetchTags = useCallback(async () => {
        try {
            const response = await api.get('/resources/tags');
            setAvailableTags(response.data ?? []);
            // Clear any selected tags that no longer exist
            setSelectedTags(prev => prev.filter(tag => response.data?.includes(tag)));
        } catch {
            // Silently fail - tags filter just won't be populated
        }
    }, []);

    // Fetch tags on mount
    useEffect(() => {
        fetchTags();
    }, [fetchTags]);

    const pageSize = 10;
    const paginationParams = useMemo(
        () => ({
            q: searchQuery || undefined,
            status: currentFilter,
            sort_by: sortBy,
            sort_order: sortOrder,
            tags: selectedTags.length > 0 ? selectedTags : undefined,
        }),
        [searchQuery, currentFilter, sortBy, sortOrder, selectedTags]
    );

    const fetchResources = useCallback(
        async ({
            cursor,
            limit,
            q,
            status,
            sort_by,
            sort_order,
            tags,
        }: {
            cursor?: string | null;
            limit: number;
            q?: string;
            status?: string;
            sort_by?: string;
            sort_order?: string;
            tags?: string[];
        }) => {
            const response = await api.get('/resources/search', {
                params: {
                    cursor,
                    limit,
                    q,
                    status,
                    sort_by,
                    sort_order,
                    tags,
                },
            });
            return response.data;
        },
        []
    );

    const {
        items: resources,
        hasMore,
        loading,
        totalCount,
        loadMore,
        refresh,
    } = usePagination<Resource, typeof paginationParams>(fetchResources, {
        params: paginationParams,
        limit: pageSize,
    });

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
            await refresh();
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
                        {isAdmin && (
                            <TagManager onTagsChanged={() => {
                                fetchTags();
                                refresh();
                                onRefresh();
                            }} />
                        )}
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
                                }}
                                className="pl-9"
                            />
                        </div>
                        <Select value={sortBy} onValueChange={setSortBy}>
                            <SelectTrigger className="w-[140px]">
                                <SelectValue placeholder="Sort by" />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="name">Name</SelectItem>
                                <SelectItem value="status">Status</SelectItem>
                                <SelectItem value="id">ID</SelectItem>
                            </SelectContent>
                        </Select>
                        <Button
                            variant="secondary"
                            size="sm"
                            className="gap-2 rounded-full border border-primary/30 bg-primary/5 text-sm font-semibold"
                            onClick={() => setSortOrder(order => (order === 'asc' ? 'desc' : 'asc'))}
                        >
                            {sortOrder === 'asc' ? (
                                <>
                                    <ArrowUpWideNarrow className="h-4 w-4" />
                                    Ascending
                                </>
                            ) : (
                                <>
                                    <ArrowDownWideNarrow className="h-4 w-4" />
                                    Descending
                                </>
                            )}
                        </Button>
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

                    {/* Tag Filter */}
                    {availableTags.length > 0 && (
                        <div className="mb-4">
                            <div className="flex flex-wrap items-center gap-2">
                                <span className="text-sm text-muted-foreground flex items-center gap-1">
                                    <Tag className="h-3 w-3" />
                                    Filter by tags:
                                </span>
                                {availableTags.map(tag => (
                                    <Button
                                        key={tag}
                                        variant={selectedTags.includes(tag) ? 'default' : 'outline'}
                                        size="sm"
                                        onClick={() => {
                                            setSelectedTags(prev =>
                                                prev.includes(tag)
                                                    ? prev.filter(t => t !== tag)
                                                    : [...prev, tag]
                                            );
                                        }}
                                        className="h-7 text-xs"
                                    >
                                        {tag}
                                    </Button>
                                ))}
                                {selectedTags.length > 0 && (
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        onClick={() => setSelectedTags([])}
                                        className="h-7 text-xs text-muted-foreground"
                                    >
                                        <X className="h-3 w-3 mr-1" />
                                        Clear tags
                                    </Button>
                                )}
                            </div>
                        </div>
                    )}

                    {/* Resource List */}
                    <div className="space-y-2">
                        {loading && resources.length === 0 ? (
                            <div className="space-y-3">
                                {[...Array(3)].map((_, index) => (
                                    <Skeleton key={index} className="h-16 w-full" />
                                ))}
                            </div>
                        ) : resources.length === 0 ? (
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
                                        setSelectedTags([]);
                                    }}
                                >
                                    Clear Filters
                                </Button>
                            </div>
                        ) : (
                            resources.map(resource => {
                                const tags = Array.isArray(resource.tags) ? resource.tags : [];
                                return (
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
                                            {resource.description && (
                                                <p className="text-sm text-muted-foreground mt-0.5 line-clamp-2">
                                                    {resource.description}
                                                </p>
                                            )}
                                            <div className="flex flex-wrap items-center gap-2 mt-1">
                                                <Badge
                                                    variant={getStatusVariant(resource)}
                                                    className="cursor-pointer gap-1"
                                                    onClick={() => handleToggleStatus(resource)}
                                                >
                                                    {getStatusIcon(resource)}
                                                    {getStatusText(resource)}
                                                </Badge>
                                                {/* Display labels */}
                                                {resource.labels && resource.labels.length > 0 && (
                                                    <LabelBadgeList
                                                        labels={resource.labels as LabelData[]}
                                                        maxDisplay={3}
                                                        size="sm"
                                                        showCategory={false}
                                                    />
                                                )}
                                                {/* Legacy tags fallback */}
                                                {tags.slice(0, 3).map(tag => (
                                                    <Badge key={tag} variant="outline" className="text-xs">
                                                        {tag}
                                                    </Badge>
                                                ))}
                                                {tags.length > 3 && (
                                                    <DropdownMenu>
                                                        <DropdownMenuTrigger asChild>
                                                            <button
                                                                type="button"
                                                                className="inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors cursor-pointer hover:bg-accent border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80"
                                                            >
                                                                +{tags.length - 3} more
                                                            </button>
                                                        </DropdownMenuTrigger>
                                                        <DropdownMenuContent className="max-w-md p-3" align="start">
                                                            <div className="space-y-2">
                                                                <h4 className="font-medium text-sm mb-2">All Tags</h4>
                                                                <div className="flex flex-wrap gap-1.5 max-h-64 overflow-y-auto">
                                                                    {tags.slice(3).map(tag => (
                                                                        <Badge key={tag} variant="outline" className="text-xs">
                                                                            {tag}
                                                                        </Badge>
                                                                    ))}
                                                                </div>
                                                            </div>
                                                        </DropdownMenuContent>
                                                    </DropdownMenu>
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
                                            <EditResourceDialog
                                                resource={resource}
                                                onSuccess={() => {
                                                    refresh();
                                                    onRefresh();
                                                }}
                                                disabled={!isAdmin}
                                            />
                                            <BusinessHoursEditor
                                                resourceId={resource.id}
                                                resourceName={resource.name}
                                                isAdmin={true}
                                            />
                                            {resource.available && (
                                                <Button size="sm" onClick={() => handleReserve(resource)}>
                                                    Reserve
                                                </Button>
                                            )}
                                        </div>
                                    </div>
                                );
                            })
                        )}
                    </div>

                    <Pagination
                        hasMore={hasMore}
                        loading={loading}
                        onLoadMore={loadMore}
                        summary={
                            totalCount !== null
                                ? `Showing ${resources.length} of ${totalCount} resources`
                                : `Showing ${resources.length} resources`
                        }
                    />
                </CardContent>
            </Card>

            {/* Dialogs */}
            <CreateResourceDialog
                open={createDialogOpen}
                onOpenChange={setCreateDialogOpen}
                onSuccess={() => {
                    void refresh();
                    onRefresh();
                }}
            />
            <UploadCsvDialog
                open={uploadDialogOpen}
                onOpenChange={setUploadDialogOpen}
                onSuccess={() => {
                    void refresh();
                    onRefresh();
                }}
            />
            <ReservationDialog
                open={reservationDialogOpen}
                onOpenChange={setReservationDialogOpen}
                resource={selectedResource}
                onSuccess={() => {
                    void refresh();
                    onRefresh();
                }}
            />
            <AvailabilityDialog
                open={availabilityDialogOpen}
                onOpenChange={setAvailabilityDialogOpen}
                resource={selectedResource}
            />
        </>
    );
}
