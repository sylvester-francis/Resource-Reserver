"use client";

import { useState, useEffect } from 'react';
import {
  ChevronRight,
  ChevronDown,
  Folder,
  FolderOpen,
  Building,
  Layers,
  Loader2,
  Plus,
} from 'lucide-react';

import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import { resourceGroupsApi } from '@/lib/api';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';

interface ResourceGroup {
  id: number;
  name: string;
  description?: string;
  parent_id?: number;
  building?: string;
  floor?: string;
  room?: string;
  children?: ResourceGroup[];
  resources?: { id: number; name: string }[];
}

interface ResourceGroupTreeProps {
  onSelectGroup?: (groupId: number | null) => void;
  selectedGroupId?: number | null;
  isAdmin?: boolean;
}

export function ResourceGroupTree({
  onSelectGroup,
  selectedGroupId,
  isAdmin = false,
}: ResourceGroupTreeProps) {
  const [loading, setLoading] = useState(true);
  const [groups, setGroups] = useState<ResourceGroup[]>([]);
  const [buildings, setBuildings] = useState<string[]>([]);
  const [expandedGroups, setExpandedGroups] = useState<Set<number>>(new Set());
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [newGroupName, setNewGroupName] = useState('');
  const [newGroupDescription, setNewGroupDescription] = useState('');
  const [newGroupParentId, setNewGroupParentId] = useState<number | null>(null);
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [treeResponse, buildingsResponse] = await Promise.all([
        resourceGroupsApi.getTree(),
        resourceGroupsApi.getBuildings(),
      ]);
      setGroups(treeResponse.data || []);
      setBuildings(buildingsResponse.data || []);
    } catch (error) {
      console.error('Failed to fetch resource groups:', error);
      toast.error('Failed to load resource groups');
    } finally {
      setLoading(false);
    }
  };

  const toggleExpand = (groupId: number) => {
    setExpandedGroups(prev => {
      const next = new Set(prev);
      if (next.has(groupId)) {
        next.delete(groupId);
      } else {
        next.add(groupId);
      }
      return next;
    });
  };

  const handleSelectGroup = (groupId: number | null) => {
    onSelectGroup?.(groupId);
  };

  const handleCreateGroup = async () => {
    if (!newGroupName.trim()) return;

    setCreating(true);
    try {
      await resourceGroupsApi.create({
        name: newGroupName.trim(),
        description: newGroupDescription.trim() || undefined,
        parent_id: newGroupParentId ?? undefined,
      });
      toast.success('Group created');
      setCreateDialogOpen(false);
      setNewGroupName('');
      setNewGroupDescription('');
      setNewGroupParentId(null);
      fetchData();
    } catch (error) {
      toast.error('Failed to create group', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    } finally {
      setCreating(false);
    }
  };

  const renderGroupNode = (group: ResourceGroup, depth: number = 0) => {
    const hasChildren = group.children && group.children.length > 0;
    const isExpanded = expandedGroups.has(group.id);
    const isSelected = selectedGroupId === group.id;

    return (
      <div key={group.id}>
        <div
          className={cn(
            "flex items-center gap-2 py-1.5 px-2 rounded-md cursor-pointer transition-colors",
            isSelected
              ? "bg-primary/10 text-primary"
              : "hover:bg-muted/60"
          )}
          style={{ paddingLeft: `${depth * 16 + 8}px` }}
          onClick={() => handleSelectGroup(group.id)}
        >
          {hasChildren ? (
            <button
              onClick={(e) => {
                e.stopPropagation();
                toggleExpand(group.id);
              }}
              className="p-0.5 hover:bg-muted rounded"
            >
              {isExpanded ? (
                <ChevronDown className="h-4 w-4" />
              ) : (
                <ChevronRight className="h-4 w-4" />
              )}
            </button>
          ) : (
            <span className="w-5" />
          )}

          {isExpanded ? (
            <FolderOpen className="h-4 w-4 text-muted-foreground" />
          ) : (
            <Folder className="h-4 w-4 text-muted-foreground" />
          )}

          <span className="text-sm flex-1 truncate">{group.name}</span>

          {group.resources && group.resources.length > 0 && (
            <span className="text-xs text-muted-foreground">
              {group.resources.length}
            </span>
          )}
        </div>

        {hasChildren && isExpanded && (
          <div>
            {group.children!.map(child => renderGroupNode(child, depth + 1))}
          </div>
        )}
      </div>
    );
  };

  if (loading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    );
  }

  return (
    <>
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base flex items-center gap-2">
              <Layers className="h-4 w-4" />
              Resource Groups
            </CardTitle>
            {isAdmin && (
              <Button
                variant="ghost"
                size="icon-sm"
                onClick={() => setCreateDialogOpen(true)}
                title="Create group"
              >
                <Plus className="h-4 w-4" />
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent className="space-y-2">
          <button
            className={cn(
              "w-full flex items-center gap-2 py-1.5 px-2 rounded-md cursor-pointer transition-colors text-left",
              selectedGroupId === null
                ? "bg-primary/10 text-primary"
                : "hover:bg-muted/60"
            )}
            onClick={() => handleSelectGroup(null)}
          >
            <span className="w-5" />
            <Layers className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm">All Resources</span>
          </button>

          <Separator />

          {buildings.length > 0 && (
            <div className="space-y-1">
              <p className="text-xs text-muted-foreground uppercase tracking-wider px-2 py-1">
                Buildings
              </p>
              {buildings.map(building => (
                <div
                  key={building}
                  className="flex items-center gap-2 py-1.5 px-2 rounded-md hover:bg-muted/60 cursor-pointer"
                >
                  <span className="w-5" />
                  <Building className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm">{building}</span>
                </div>
              ))}
              <Separator className="my-2" />
            </div>
          )}

          {groups.length > 0 ? (
            <div className="space-y-0.5">
              {groups.map(group => renderGroupNode(group))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground text-center py-4">
              No groups created yet
            </p>
          )}
        </CardContent>
      </Card>

      <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create Resource Group</DialogTitle>
            <DialogDescription>
              Create a new group to organize resources.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="group-name">Name</Label>
              <Input
                id="group-name"
                value={newGroupName}
                onChange={(e) => setNewGroupName(e.target.value)}
                placeholder="e.g., Conference Rooms"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="group-description">Description (optional)</Label>
              <Input
                id="group-description"
                value={newGroupDescription}
                onChange={(e) => setNewGroupDescription(e.target.value)}
                placeholder="Description of this group"
              />
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setCreateDialogOpen(false)}
              disabled={creating}
            >
              Cancel
            </Button>
            <Button
              onClick={handleCreateGroup}
              disabled={creating || !newGroupName.trim()}
            >
              {creating && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Create Group
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
