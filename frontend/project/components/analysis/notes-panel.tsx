import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { FileText } from "lucide-react"
import type { ClinicalNote } from "@/lib/patient-data"

interface NotesPanelProps {
  notes: ClinicalNote[]
}

export function NotesPanel({ notes }: NotesPanelProps) {
  return (
    <Card className="h-full">
      <CardHeader className="pb-2">
        <div className="flex items-center gap-2">
          <FileText className="h-5 w-5 text-muted-foreground" />
          <CardTitle className="text-lg font-semibold">Clinical Notes</CardTitle>
        </div>
      </CardHeader>
      <CardContent>
        <ul className="flex flex-col gap-2">
          {notes.map((note) => (
            <li
              key={note.id}
              className="flex items-start gap-3 rounded-lg border border-border bg-muted/30 p-3"
            >
              <div className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
              <div className="flex-1">
                <p className="text-sm text-foreground">{note.content}</p>
                <p className="mt-1 text-xs text-muted-foreground">{note.timestamp}</p>
              </div>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  )
}
