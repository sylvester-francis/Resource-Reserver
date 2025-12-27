/**
 * Webhook Settings component.
 */

"use client";

import { useState, useEffect } from 'react';
import {
  Webhook,
  Plus,
  Trash2,
  RefreshCw,
  Play,
  Copy,
  Check,
  Loader2,
  ChevronDown,
  ChevronUp,
  AlertCircle,
  CheckCircle2,
  XCircle,
} from 'lucide-react';

import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
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
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { webhooksApi } from '@/lib/api';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';

interface WebhookData {
  id: number;
  url: string;
  events: string[];
  description?: string;
  is_active: boolean;
  secret?: string;
  created_at: string;
}

interface WebhookDelivery {
  id: number;
  event_type: string;
  status: string;
  status_code?: number;
  error_message?: string;
  created_at: string;
  delivered_at?: string;
}

interface EventType {
  type: string;
  description: string;
}

export function WebhookSettings() {
  const [loading, setLoading] = useState(true);
  const [webhooks, setWebhooks] = useState<WebhookData[]>([]);
  const [eventTypes, setEventTypes] = useState<EventType[]>([]);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [webhookToDelete, setWebhookToDelete] = useState<number | null>(null);
  const [expandedWebhook, setExpandedWebhook] = useState<number | null>(null);
  const [deliveries, setDeliveries] = useState<Record<number, WebhookDelivery[]>>({});
  const [loadingDeliveries, setLoadingDeliveries] = useState<number | null>(null);

  const [newUrl, setNewUrl] = useState('');
  const [newDescription, setNewDescription] = useState('');
  const [newEvents, setNewEvents] = useState<string[]>([]);
  const [creating, setCreating] = useState(false);
  const [copiedSecret, setCopiedSecret] = useState<number | null>(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [webhooksRes, eventsRes] = await Promise.all([
        webhooksApi.list(),
        webhooksApi.getEventTypes(),
      ]);
      setWebhooks(webhooksRes.data || []);
      setEventTypes(eventsRes.data || []);
    } catch (error) {
      console.error('Failed to fetch webhooks:', error);
      toast.error('Failed to load webhooks');
    } finally {
      setLoading(false);
    }
  };

  const fetchDeliveries = async (webhookId: number) => {
    setLoadingDeliveries(webhookId);
    try {
      const response = await webhooksApi.getDeliveries(webhookId);
      setDeliveries(prev => ({ ...prev, [webhookId]: response.data || [] }));
    } catch (error) {
      console.error('Failed to fetch deliveries:', error);
    } finally {
      setLoadingDeliveries(null);
    }
  };

  const handleCreate = async () => {
    if (!newUrl || newEvents.length === 0) return;

    setCreating(true);
    try {
      const response = await webhooksApi.create({
        url: newUrl,
        events: newEvents,
        description: newDescription || undefined,
      });
      setWebhooks(prev => [...prev, response.data]);
      toast.success('Webhook created', {
        description: 'Save the secret shown - it will not be displayed again.',
      });
      setCreateDialogOpen(false);
      setNewUrl('');
      setNewDescription('');
      setNewEvents([]);
    } catch (error) {
      toast.error('Failed to create webhook', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async () => {
    if (!webhookToDelete) return;

    try {
      await webhooksApi.delete(webhookToDelete);
      setWebhooks(prev => prev.filter(w => w.id !== webhookToDelete));
      toast.success('Webhook deleted');
    } catch (error) {
      toast.error('Failed to delete webhook', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    } finally {
      setDeleteDialogOpen(false);
      setWebhookToDelete(null);
    }
  };

  const handleToggleActive = async (webhook: WebhookData) => {
    try {
      await webhooksApi.update(webhook.id, { is_active: !webhook.is_active });
      setWebhooks(prev =>
        prev.map(w =>
          w.id === webhook.id ? { ...w, is_active: !w.is_active } : w
        )
      );
      toast.success(webhook.is_active ? 'Webhook disabled' : 'Webhook enabled');
    } catch {
      toast.error('Failed to update webhook');
    }
  };

  const handleTest = async (webhookId: number) => {
    try {
      const response = await webhooksApi.test(webhookId);
      if (response.data.success) {
        toast.success('Test webhook sent successfully');
      } else {
        toast.error('Test webhook failed', {
          description: response.data.message,
        });
      }
      fetchDeliveries(webhookId);
    } catch {
      toast.error('Failed to send test webhook');
    }
  };

  const handleRegenerateSecret = async (webhookId: number) => {
    try {
      const response = await webhooksApi.regenerateSecret(webhookId);
      setWebhooks(prev =>
        prev.map(w =>
          w.id === webhookId ? { ...w, secret: response.data.secret } : w
        )
      );
      toast.success('Secret regenerated', {
        description: 'Save the new secret - it will not be displayed again.',
      });
    } catch {
      toast.error('Failed to regenerate secret');
    }
  };

  const handleCopySecret = async (webhookId: number, secret: string) => {
    try {
      await navigator.clipboard.writeText(secret);
      setCopiedSecret(webhookId);
      setTimeout(() => setCopiedSecret(null), 2000);
    } catch {
      toast.error('Failed to copy secret');
    }
  };

  const toggleEventSelection = (eventType: string) => {
    setNewEvents(prev =>
      prev.includes(eventType)
        ? prev.filter(e => e !== eventType)
        : [...prev, eventType]
    );
  };

  const handleExpandWebhook = (webhookId: number) => {
    if (expandedWebhook === webhookId) {
      setExpandedWebhook(null);
    } else {
      setExpandedWebhook(webhookId);
      if (!deliveries[webhookId]) {
        fetchDeliveries(webhookId);
      }
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-semibold flex items-center gap-2">
              <Webhook className="h-6 w-6" />
              Webhooks
            </h2>
            <p className="text-sm text-muted-foreground">
              Receive HTTP notifications for reservation events
            </p>
          </div>
          <Button onClick={() => setCreateDialogOpen(true)} className="gap-2">
            <Plus className="h-4 w-4" />
            Add Webhook
          </Button>
        </div>

        {webhooks.length === 0 ? (
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-12 text-center">
              <Webhook className="h-12 w-12 text-muted-foreground/50 mb-4" />
              <h3 className="text-lg font-medium mb-1">No webhooks configured</h3>
              <p className="text-sm text-muted-foreground mb-4">
                Add a webhook to receive notifications for reservation events
              </p>
              <Button onClick={() => setCreateDialogOpen(true)} className="gap-2">
                <Plus className="h-4 w-4" />
                Add Webhook
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-4">
            {webhooks.map(webhook => (
              <Card key={webhook.id}>
                <CardContent className="p-4">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-mono text-sm truncate">
                          {webhook.url}
                        </span>
                        <Badge variant={webhook.is_active ? "default" : "secondary"}>
                          {webhook.is_active ? 'Active' : 'Inactive'}
                        </Badge>
                      </div>
                      {webhook.description && (
                        <p className="text-sm text-muted-foreground mb-2">
                          {webhook.description}
                        </p>
                      )}
                      <div className="flex flex-wrap gap-1">
                        {webhook.events.map(event => (
                          <Badge key={event} variant="outline" className="text-xs">
                            {event}
                          </Badge>
                        ))}
                      </div>

                      {webhook.secret && (
                        <div className="mt-3 p-2 bg-muted/50 rounded-md flex items-center gap-2">
                          <code className="text-xs flex-1 truncate">
                            {webhook.secret}
                          </code>
                          <Button
                            variant="ghost"
                            size="icon-sm"
                            onClick={() => handleCopySecret(webhook.id, webhook.secret!)}
                          >
                            {copiedSecret === webhook.id ? (
                              <Check className="h-3 w-3 text-green-500" />
                            ) : (
                              <Copy className="h-3 w-3" />
                            )}
                          </Button>
                        </div>
                      )}
                    </div>

                    <div className="flex items-center gap-2">
                      <Switch
                        checked={webhook.is_active}
                        onCheckedChange={() => handleToggleActive(webhook)}
                      />
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        onClick={() => handleTest(webhook.id)}
                        title="Send test webhook"
                      >
                        <Play className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        onClick={() => handleRegenerateSecret(webhook.id)}
                        title="Regenerate secret"
                      >
                        <RefreshCw className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        onClick={() => {
                          setWebhookToDelete(webhook.id);
                          setDeleteDialogOpen(true);
                        }}
                        title="Delete webhook"
                        className="text-destructive hover:text-destructive"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>

                  <Separator className="my-3" />

                  <button
                    className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
                    onClick={() => handleExpandWebhook(webhook.id)}
                  >
                    {expandedWebhook === webhook.id ? (
                      <ChevronUp className="h-4 w-4" />
                    ) : (
                      <ChevronDown className="h-4 w-4" />
                    )}
                    Delivery History
                  </button>

                  {expandedWebhook === webhook.id && (
                    <div className="mt-3">
                      {loadingDeliveries === webhook.id ? (
                        <div className="flex items-center justify-center py-4">
                          <Loader2 className="h-4 w-4 animate-spin" />
                        </div>
                      ) : deliveries[webhook.id]?.length ? (
                        <div className="space-y-2">
                          {deliveries[webhook.id].slice(0, 10).map(delivery => (
                            <div
                              key={delivery.id}
                              className="flex items-center justify-between p-2 bg-muted/30 rounded text-sm"
                            >
                              <div className="flex items-center gap-2">
                                {delivery.status === 'delivered' ? (
                                  <CheckCircle2 className="h-4 w-4 text-green-500" />
                                ) : delivery.status === 'failed' ? (
                                  <XCircle className="h-4 w-4 text-destructive" />
                                ) : (
                                  <AlertCircle className="h-4 w-4 text-yellow-500" />
                                )}
                                <span>{delivery.event_type}</span>
                                {delivery.status_code && (
                                  <Badge variant="outline" className="text-xs">
                                    {delivery.status_code}
                                  </Badge>
                                )}
                              </div>
                              <span className="text-xs text-muted-foreground">
                                {new Date(delivery.created_at).toLocaleString()}
                              </span>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="text-sm text-muted-foreground text-center py-4">
                          No deliveries yet
                        </p>
                      )}
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>

      <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Create Webhook</DialogTitle>
            <DialogDescription>
              Add a webhook to receive HTTP notifications for events
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="webhook-url">URL</Label>
              <Input
                id="webhook-url"
                type="url"
                value={newUrl}
                onChange={(e) => setNewUrl(e.target.value)}
                placeholder="https://example.com/webhook"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="webhook-description">Description (optional)</Label>
              <Input
                id="webhook-description"
                value={newDescription}
                onChange={(e) => setNewDescription(e.target.value)}
                placeholder="My integration webhook"
              />
            </div>

            <div className="space-y-2">
              <Label>Events</Label>
              <div className="grid grid-cols-2 gap-2 max-h-48 overflow-y-auto">
                {eventTypes.map(event => (
                  <button
                    key={event.type}
                    onClick={() => toggleEventSelection(event.type)}
                    className={cn(
                      "p-2 rounded-md border text-left text-sm transition-colors",
                      newEvents.includes(event.type)
                        ? "border-primary bg-primary/10"
                        : "border-border hover:bg-muted/60"
                    )}
                  >
                    <span className="font-medium">{event.type}</span>
                  </button>
                ))}
              </div>
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
              onClick={handleCreate}
              disabled={creating || !newUrl || newEvents.length === 0}
            >
              {creating && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Create Webhook
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Webhook</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete this webhook? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete} className="bg-destructive text-white hover:bg-destructive/90">
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
