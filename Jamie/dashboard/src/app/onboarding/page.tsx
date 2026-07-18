"use client";

import { useEffect, useState, useCallback } from "react";
import { getOnboardingRecords } from "@/lib/jamie-db";
import { getGuilds } from "@/lib/discord";
import Link from "next/link";
import { useRouter } from "next/navigation";

interface Guild {
  id: string;
  name: string;
  icon: string | null;
}

interface OnboardingRecord {
  user_id: string;
  guild_id: string;
  started_at: string;
  completed_at: string | null;
  status: string;
  personality_data: string;
  interests: string;
}

export default function OnboardingPage() {
  const [guilds, setGuilds] = useState<Guild[]>([]);
  const [selectedGuildId, setSelectedGuildId] = useState<string>("");
  const [records, setRecords] = useState<OnboardingRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  useEffect(() => {
    const loadGuilds = async () => {
      try {
        const data = await getGuilds();
        setGuilds(data);
        if (data.length > 0) {
          setSelectedGuildId(data[0].id);
        }
      } catch (e) {
        console.error("Failed to load guilds:", e);
      }
    };
    loadGuilds();
  }, []);

  const loadRecords = useCallback(async (guildId: string) => {
    if (!guildId) return;
    setLoading(true);
    try {
      const data = await getOnboardingRecords(guildId);
      setRecords(data);
    } catch (e) {
      console.error("Failed to load onboarding records:", e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (selectedGuildId) {
      loadRecords(selectedGuildId);
    }
  }, [selectedGuildId, loadRecords]);

  const getStatusColor = (status: string) => {
    switch (status) {
      case "completed":
        return "bg-green-100 text-green-800";
      case "pending":
        return "bg-yellow-100 text-yellow-800";
      case "cancelled":
        return "bg-red-100 text-red-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  return (
    <main className="flex-1 ml-[240px] p-8" style={{ background: "var(--bg)" }}>
      <div className="flex min-h-screen">
        <div className="flex-1">
          <h1 className="text-3xl font-bold mb-6">📝 Onboarding Records</h1>

          {/* Guild selector */}
          <div className="card p-4 mb-6">
            <label className="block text-sm font-medium mb-2">Select Server</label>
            <select
              value={selectedGuildId}
              onChange={(e) => setSelectedGuildId(e.target.value)}
              className="input"
            >
              {guilds.map((g) => (
                <option key={g.id} value={g.id}>
                  {g.name}
                </option>
              ))}
            </select>
          </div>

          {/* Records table */}
          {loading ? (
            <div className="text-center py-8">Loading records...</div>
          ) : records.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              No onboarding records found for this server.
            </div>
          ) : (
            <div className="card overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-100">
                    <tr>
                      <th className="p-3 text-left">User</th>
                      <th className="p-3 text-left">Status</th>
                      <th className="p-3 text-left">Started</th>
                      <th className="p-3 text-left">Completed</th>
                      <th className="p-3 text-left">Personality</th>
                      <th className="p-3 text-left">Interests</th>
                    </tr>
                  </thead>
                  <tbody>
                    {records.map((record) => (
                      <tr key={`${record.user_id}-${record.guild_id}`} className="border-b">
                        <td className="p-3">
                          <div className="font-medium">User ID: {record.user_id}</div>
                        </td>
                        <td className="p-3">
                          <span className={`px-2 py-1 rounded text-xs ${getStatusColor(record.status)}`}>
                            {record.status}
                          </span>
                        </td>
                        <td className="p-3 text-sm">
                          {new Date(record.started_at).toLocaleString()}
                        </td>
                        <td className="p-3 text-sm">
                          {record.completed_at
                            ? new Date(record.completed_at).toLocaleString()
                            : "-"}
                        </td>
                        <td className="p-3 text-sm max-w-xs truncate" title={record.personality_data}>
                          {record.personality_data || "N/A"}
                        </td>
                        <td className="p-3 text-sm max-w-xs truncate" title={record.interests}>
                          {record.interests || "N/A"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </div>
    </main>
  );
}
