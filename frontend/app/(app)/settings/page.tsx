"use client";

import Link from "next/link";
import { Settings } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default function SettingsPage() {
  return (
    <div
      className="mx-auto flex max-w-6xl items-center justify-center px-4 py-16 sm:px-6 lg:px-8"
      data-testid="settings-placeholder"
    >
      <Card className="w-full max-w-md text-center">
        <CardHeader>
          <span className="mx-auto mb-2 flex size-10 items-center justify-center rounded-lg bg-primary/15 text-primary">
            <Settings className="size-5" />
          </span>
          <CardTitle className="text-lg">Settings</CardTitle>
          <CardDescription>
            Profile, notification and workspace preferences are coming soon.
            Your account is managed through your role — talk to an admin to
            change access.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button
            render={<Link href="/dashboard" />}
            nativeButton={false}
            variant="outline"
            className="w-full"
          >
            Back to dashboard
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
